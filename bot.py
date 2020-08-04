import sys
import os
import datetime
import json
import discord
import docker
from discord.ext import commands
from pathlib import Path

arg_dict = dict((arg[2:], val) for arg, val in [arg.split("=") for arg in sys.argv[1:] if arg.startswith("--")])

LOGFILE = "./latest.log"
PERMISSIONS_FILE = "./permissions.json"

TOKEN = os.environ['DISCORD_TOKEN_CARINAE_SERVER_BOT']
description = """Carinae Server Status bot designed to manage the various carinae game servers.
Can be used to check status, start/stop and perform backup related server tasks."""
idle_activity_state = discord.Activity(name="$help", type=discord.ActivityType.listening)
json_permissions = None
docker_client = docker.client.from_env()
bot = commands.Bot(command_prefix='$',
                   description=description,
                   activity=idle_activity_state)
uptime_start = datetime.datetime.now()
emojis = {
    "ok_hand": "\U0001F44C",
    "keycap_#": "\u0023",
    "keycap_*": "\u002A",
    "keycap_0": "\u0030",
    "keycap_1": "\u0031",
    "keycap_2": "\u0032",
    "keycap_3": "\u0033"
}


def log(msg, category="INFO"):
    with open(LOGFILE, "a") as f:
        logtime = datetime.datetime.now()
        out = f"[{logtime}]:\t[{category}]\t{msg}\n"
        f.write(out)
        print(out.rstrip("\n"))


def log_unauthorized(ctx, *servers):
    log(f"Function {ctx.command.name} was called by user {ctx.author} (id: {ctx.author.id}) in channel {ctx.channel} "
        f"for server(s): [{', '.join(servers)}], "
        f"but user is not authorized.", category="FORBIDDEN")


try:
    log(f"Loading permissions from {PERMISSIONS_FILE}...")
    with open(PERMISSIONS_FILE) as perm_json:
        json_permissions = json.load(perm_json)
        log(f"Permissions loaded.")
except FileNotFoundError:
    log(f"Permissions file does not exist - creating default schema.", category="WARNING")
    try:
        Path(PERMISSIONS_FILE).touch()
    except FileExistsError:
        log(f"The file {PERMISSIONS_FILE} was not detected when loading permissions, but is raising FileExistsError "
            f"when attempting to touch!  This is less than ideal...",
            category="ERROR")
        raise
except PermissionError as e:
    log(f"Permission error encountered while trying to read the permissions json file: {e.errno}: {e.strerror}",
        category="ERROR")
except OSError as e:
    log(f"Error opening permissions file: {e.errno}: {e.strerror}", category="ERROR")
    sys.exit()


def perm_check(ctx):
    if str(ctx.author.id) in json_permissions["users"]["admins"]:
        return [container.name for container in docker_client.containers.list(all=True)]
    else:
        return [server["name"] for server in json_permissions["servers"] if str(ctx.author.id) in server[ctx.command.name]]


@bot.event
async def on_ready():
    log("Discord bot ready and waiting!")
    for server in bot.guilds:
        log(f"Connected to '{server.name}' (id: {server.id})")


@bot.command(category="Server")
async def status(ctx: discord.ext.commands.context, *servers: str):
    """Displays the status of the specified server.  If no server is specified, displays the status of all servers."""
    log(f"Status command received from channel {ctx.channel} by {ctx.author} (id: {ctx.author.id})")
    autofilled = False

    if not servers:
        # add all servers to list if none were passed
        servers = perm_check(ctx)
        autofilled = True

    if len(servers) > 1:
        embed = discord.Embed(title="Server Statuses")
        async with ctx.typing():
            for server in servers:
                if server in perm_check(ctx):
                    try:
                        embed.add_field(name=server,
                                        value=docker_client.containers.get(server).status.title(),
                                        inline=True)
                    except docker.errors.NotFound:
                        embed.add_field(name=server, value="Not Found/Invalid Name", inline=True)
                elif not autofilled:
                    log_unauthorized(ctx, server)
                    embed.add_field(name=server, value="Not Found/Invalid Name", inline=True)

        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title=f"{servers[0]} Detailed Status Report")
        async with ctx.typing():
            for server in servers:
                if server in perm_check(ctx):
                    try:
                        container = docker_client.containers.get(server)

                        embed.add_field(name="Docker Status", value=container.status.title(), inline=True)

                        if container.status == 'running':
                            embed.add_field(name="Server Uptime",
                                            value=container.exec_run("uptime").output.decode('utf-8'),
                                            inline=True)
                            embed.add_field(name="World Size (Minecraft)",
                                            value=container.exec_run("du -h world/level.dat").output.decode('utf-8'),
                                            inline=True)
                            embed.add_field(name="Log Tail",
                                            value=container.exec_run("tail -n3 logs/latest.log").output.decode('utf-8'),
                                            inline=False)

                    except docker.errors.NotFound:
                        embed.add_field(name=server, value="Not Found/Invalid Name", inline=True)
                elif not autofilled:
                    log_unauthorized(ctx, server)
                    embed.add_field(name=server, value="Not Found/Invalid Name", inline=True)
        await ctx.send(embed=embed)


@bot.command()
async def restart(ctx, *servers: str):
    """Attempts to restart the specified server.  Starts the server if it is not already running."""
    log(f"Executing restart command for {','.join([server for server in servers])} from {ctx.channel}, "
        f"initiated by {ctx.author}")
    embed = discord.Embed(title="Restart Results")
    async with ctx.typing():
        for server in servers:
            if server in perm_check(ctx):
                try:
                    container = docker_client.containers.get(server)
                    container.restart()
                    embed.add_field(name=server, value="Restart Sent", inline=True)
                except docker.errors.NotFound:
                    embed.add_field(name=server, value="Not Found/Invalid Name", inline=True)
            else:
                log_unauthorized(ctx, server)
                embed.add_field(name=server, value="Not Found/Invalid Name", inline=True)
    await ctx.send(embed=embed)


@bot.command(hidden=True)
async def kill(ctx, *servers: str):
    """Kills the specified carinae server with a sigkill.  This is not safe and can result in data loss or server
    corruption!  Use only as a last resort! """
    log(f"Executing the kill command for {','.join([server for server in servers])} from {ctx.channel}")
    embed = discord.Embed(title="SIGKILL Results")
    for server in servers:
        if server in perm_check(ctx):
            try:
                container = docker_client.containers.get(server)
                container.kill()
                embed.add_field(name=server, value=f"SIGKILL Sent - status is {container.status}", inline=True)
            except docker.errors.NotFound:
                embed.add_field(name=server, value="Not Found/Invalid Name", inline=True)
        else:
            log_unauthorized(ctx, server)
            embed.add_field(name=server, value="Not Found/Invalid Name", inline=True)
    await ctx.send(embed=embed)


@bot.command()
async def start(ctx, *servers: str):
    """Starts the specified carinae server.  Does nothing if the specified server is already running."""
    log(f"Executing the start command for {','.join([server for server in servers])} from {ctx.channel}")
    embed = discord.Embed(title="Start Results")
    for server in servers:
        if server in perm_check(ctx):
            try:
                container = docker_client.containers.get(server)
                container.start()
                embed.add_field(name=server, value=container.status, inline=True)
            except docker.errors.NotFound:
                embed.add_field(name=server, value="Not Found/Invalid Name", inline=True)
        else:
            log_unauthorized(ctx, server)
            embed.add_field(name=server, value="Not Found/Invalid Name", inline=True)
    await ctx.send(embed=embed)


@bot.command(enabled=False, aliases=["command", "send"])
async def cmd(ctx, server: str, command: str):
    """Sends the specified command to the specified server via exec -dt syntax"""
    log(f"Executing remote command function imposed by {ctx.author} (id: {ctx.author.id}) for server {server}"
        f" - command: {command}")
    async with ctx.typing():
        if server in perm_check(ctx):
            try:
                container = docker_client.containers.get(server)
                cmd_output = container.exec_run(command).output.decode('utf-8')
                await ctx.send(f"Command output:\n{cmd_output}")
            except docker.errors.NotFound:
                await ctx.send(f"Server {server} Not Found/Invalid Name")
        else:
            log_unauthorized(ctx, server)


@bot.command(enabled=False)
async def backup(ctx, server: str, *backup_name: str):
    """Creates a backup of the world file for the specified server.  This is a filesystem backup, and typically
    cannot be restored from in-game. """
    pass


@bot.command(enabled=False)
async def restore(ctx, server: str, backup_name: str):
    """Restores a server to a named file system backup.  Shuts down the server before executing and restarts after
    the backup finishes. """
    pass


@bot.command(enabled=False, alises=["backups"])
async def list_backups(ctx, server: str):
    """Lists all available filesystem backups for the specified server."""
    pass


@bot.command(hidden=True)
async def bot_uptime(ctx):
    """Gets the current uptime of the bot.  Used for debugging."""
    log(f"Uptime requested for {ctx.channel}")
    await ctx.send(f"Bot has been up for {datetime.datetime.now() - uptime_start}")


@bot.command(hidden=True)
async def permissions(ctx, action: str, user: str, target: str, perm: str):
    """Grants or revokes permissions to the specified server for the specified discord user"""
    if str(ctx.author.id) in json_permissions["users"]["admins"]:
        if target not in [server["name"] for server in json_permissions["servers"]]:
            json_permissions["servers"].append({
                "name": target,
                "backup": [],
                "cmd": [],
                "kill": [],
                "list_backups": [],
                "restart": [],
                "restore": [],
                "start": [],
                "status": [],
                "stop": [],
                "get_logs": [],
            })

        target_user = str(user) if len(ctx.message.mentions) == 0 else str(ctx.message.mentions[0].id)

        for server in [s for s in json_permissions["servers"] if s["name"] == target]:
            if perm not in server.keys():
                server[perm] = []

            if action == "grant" and target_user not in server[perm]:
                server[perm].append(target_user)
            elif action == "revoke" and target_user in server[perm]:
                server[perm] = [p for p in server[perm] if p != target_user]

        with open(PERMISSIONS_FILE, "w") as perm_file:
            perm_file.write(json.dumps(json_permissions, indent=4, sort_keys=True))

        log(f"{action.title()} {perm} permissions to {user} for server {target} at the request of admin {ctx.author}"
            f" (id: {ctx.author.id}) executed successfully.")

        if ctx.channel.type not in [discord.ChannelType.private, discord.ChannelType.group]:
            # TODO: add a countdown emoji until the deletion of the message
            # for i in range(5, 0, -1):
            #    await ctx.message.add_reaction(emojis["keycap_" + i])
            #    sleep(1)
            await ctx.message.delete(delay=5.0)

        if not ctx.author.dm_channel:
            await ctx.author.create_dm()

        async with ctx.author.dm_channel.typing():
            await ctx.author.dm_channel.send(f"Requested permissions change has been processed:\n"
                                             f"```\n{action.title()} {perm} permissions to {user} for server"
                                             f" {target} at the request of {ctx.author} (id: {ctx.author.id})```")

    else:
        log_unauthorized(ctx, "PERMISSIONS_FILE")


@bot.command(hidden=True)
async def dump_perms(ctx):
    if str(ctx.author.id) in json_permissions["users"]["admins"]:
        log(f"Dumped permissions to chat per request from admin {ctx.author} (id: {ctx.author.id})")
        await ctx.send(f"```json\n{json.dumps(json_permissions, indent=4, sort_keys=True)}```")
    else:
        log_unauthorized(ctx, "DEBUG_FUNCTION")


@bot.command()
async def get_logs(ctx, server: str, numlines: int = 10):
    """Pulls the specified number of lines from the logs/latest.log file, up to a maximum of 20 lines."""
    log(f"Log retrieval command executed for server {server} by {ctx.author} (id: {ctx.author.id})")
    _numlines = None
    try:
        _numlines = int(numlines)
    except ValueError:
        ctx.send(f"Numlines value of {numlines} is invalid, defaulting to 10.")
        _numlines = 10

    if server in perm_check(ctx):
        container = docker_client.containers.get(server)
        log_command = f"tail -n{_numlines} logs/latest.log"
        result = container.exec_run(log_command).output.decode('utf-8')

        async with ctx.channel.typing():
            try:
                await ctx.send(f'```{result}```')
            except discord.HTTPException:
                ctx.command_failed = True
                await ctx.send(f"Failed to retrieve log results.  Result length shows to be {len(result)}" 
                               f" - discord's limit is 2000 per message.")
    else:
        log_unauthorized(ctx, server)


if __name__ == "__main__":
    bot.run(TOKEN)
