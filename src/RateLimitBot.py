import discord

from os import environ

import pymongo.errors

from discord.ext import commands

from discord import default_permissions

intents = discord.Intents.all()

bot = commands.Bot(intents=intents, debug_guilds=[int(environ.get("TEST_GUILD_ID"))])

mongo_client = pymongo.MongoClient(environ.get("MONGO_URL"))

db = mongo_client["ratelimitbot"]

rate_limited_users = db["rate_limited_users"]


@bot.slash_command(name="add_user_slowmode", description="Add a user to slowmode")
@default_permissions(manage_channels=True)
async def add_user_slowmode(ctx: discord.ApplicationContext,
                            user: discord.Option(discord.User, description="The user to slowmode", required=True),
                            time: discord.Option(int, description="The time to slowmode the user for in seconds",
                                                 required=True), channel: discord.Option(discord.TextChannel,
                                                                                         description="The channel to slowmode the user for",
                                                                                         required=False)):
    if not rate_limited_users.find_one({"user_id": user.id}):
        if channel:
            rate_limited_users.insert_one({"user_id": user.id, "limits": {str(channel.id): time}})
            await ctx.respond(f"Added {user} to slowmode for {time} seconds in channel {channel.mention}")
        else:
            rate_limited_users.insert_one({"user_id": user.id, "limits": {"global": time}})
            await ctx.respond(f"Added {user} to slowmode for {time} seconds")
    else:
        db_user = rate_limited_users.find_one({"user_id": user.id})
        if channel:
            if channel.id in db_user["limits"]:
                await ctx.respond(
                    f"{user} is already in slowmode for {db_user['limits'][channel.id]} seconds in channel {channel.mention}")
            else:
                db_user["limits"][str(channel.id)] = time
                rate_limited_users.update_one({"user_id": user.id}, {"$set": {"limits": db_user["limits"]}})
                await ctx.respond(f"Added {user} to slowmode for {time} seconds in channel {channel.mention}")
        else:
            if "global" in db_user["limits"]:
                await ctx.respond(f"{user} is already in slowmode for {db_user['limits']['global']} seconds")
            else:
                db_user["limits"]["global"] = time
                rate_limited_users.update_one({"user_id": user.id}, {"$set": {"limits": db_user["limits"]}})
                await ctx.respond(f"Added {user} to slowmode for {time} seconds")


@bot.slash_command(name="remove_all_slowmode", description="Remove all users from slowmode")
@default_permissions(manage_channels=True)
async def remove_all_slowmode(ctx: discord.ApplicationContext):
    rate_limited_users.delete_many({})
    await ctx.respond("Removed all users from slowmode")


@bot.slash_command(name="remove_user_slowmode", description="Remove a user from slowmode")
@default_permissions(manage_channels=True)
async def remove_user_slowmode(ctx: discord.ApplicationContext,
                               user: discord.Option(discord.User, description="The user to remove from slowmode"),
                               channel: discord.Option(discord.TextChannel,
                                                       description="The channel to remove the user from slowmode",
                                                       required=False)):
    if not rate_limited_users.find_one({"user_id": user.id}):
        await ctx.respond(f"{user} is not in the slowmode list")
    elif channel:
        user = rate_limited_users.find_one({"user_id": user.id})
        if channel.id in user["limits"]:
            del user["limits"][channel.id]
            rate_limited_users.update_one({"user_id": user.id}, {"$set": {"limits": user["limits"]}})
            await ctx.respond(f"Removed {user} from slowmode for channel {channel.mention}")
        else:
            await ctx.respond(f"{user} is not in slowmode for channel {channel.mention}")
    else:
        rate_limited_users.delete_one({"user_id": user.id})
        await ctx.respond(f"Removed {user} from slowmode")


@bot.slash_command(name="list_slowmode_users", description="List all users in slowmode")
@default_permissions(manage_channels=True)
async def list_slowmode_users(ctx: discord.ApplicationContext):
    users = rate_limited_users.find({})
    if not users:
        await ctx.respond("There are no users in slowmode")
    else:
        response_str = ""
        for user in users:
            response_str += f"<@{user['user_id']}>:\n"
            response_str += f"Global: {user['limits']['global'] if 'global' in user['limits'] else 'None'}\n"
            for channel in user["limits"]:
                if channel != "global":
                    response_str += f"<#{channel}>: {user['limits'][channel]} seconds"
                    response_str += "\n"
            response_str += "\n"
        await ctx.respond(response_str)


@bot.event
async def on_ready():
    print("Bot is ready")


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if rate_limited_users.find_one({"user_id": message.author.id}):
        user = message.author
        db_user = rate_limited_users.find_one({"user_id": message.author.id})

        async for msg in message.channel.history(limit=50):
            if msg.author.id == user.id and msg.id != message.id:
                db_user["last_message"] = msg.created_at
                break

        if "global" in db_user["limits"]:
            if (message.created_at - db_user["last_message"]).total_seconds() < db_user["limits"]["global"]:
                await message.delete()
                await user.send(f"You are in server-wide slowmode for {db_user['limits']['global']} seconds")
        if str(message.channel.id) in db_user["limits"]:
            if (message.created_at - db_user["last_message"]).total_seconds() < db_user["limits"][
                str(message.channel.id)]:
                await message.delete()
                await user.send(
                    f"You are in slowmode for {db_user['limits'][str(message.channel.id)]} seconds in channel {message.channel.mention}")
    await bot.process_commands(message)


bot.run(environ.get("DISCORD_TOKEN"))
