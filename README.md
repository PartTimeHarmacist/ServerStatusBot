# Server Status Bot
A python powered Discord Chatbot designed to manage docker containers

Goals
===
The goal of this bot is to provide an easy to use interface via discord for the admins of various dockerized servers.
ie if an administrator needs to restart their server because it is hung, they can simply tell the bot to do that instead of needing to rely on my schedule and availability.
No hard coding of environments has been done, however - this bot will take the current environment into account, not a hard-coded one.

Requirements
===
Docker is required to run this bot, and the user running this bot must have permission to interact with the docker containers.
`pip install -r requirements.txt` will get all necessary packages required to run this bot.
Once the packages have been installed, an administrator will need to be manually set in a permissions.json file, using the below schema:
```json
{
    "servers": [],
    "users": {
        "admins": [
            "admin_discord_id_here"
        ]
    }
}
```
Once the permissions.json file has been created, the bot can be launched with `python bot.py`
It will log all command output and access errors to `./latest.log` by default. 


Available Functions
===
 Function | Description 
---|---
`help <command>` | Provides the default help text if no command is specified, or command specific help text
`restart [servers...]` | Issues a restart command to each listed server (container)
`start [servers...]` | Issues a start command to each listed server (container)
`status [servers...]` | Returns the docker container status of each listed server.  If no servers are listed, provides the status of all containers/servers the querying user has permission to check
`kill [servers...]` | Issues a SIGKILL to the specified servers.  This is potentially unsafe and can result in data loss or corruption, use only as a last resort!
`permissions [grant/revoke] <user> <permission>` | Grants or revokes a user's specified permission for the listed server.  Currently can only be used by admins.
`uptime` | Debugging command to return the bot's uptime.


Work in Progress Functions
===
Function | Description
---|---
`cmd <server> <command>` | Executes the passed command on the specified server via exec -dt syntax.
`backup <server> <backup name>` | Creates a filesystem backup of the attached volume with the specified name.
`restore <server> <backup name>` | Stops a container and replaces the existing volume with the specified volume.
`list_backups <server>` | Lists available backups for the specified server

TODO
===
- [ ] Implement command to send text/commands to stdin of a docker container, instead of through exec -dt
- [ ] Implement backup/restore system
- [ ] Rework permissions system to make more sense...
- [ ] Enable log trimming/limiting.
    - Currently the log records all, and has only the filesystem to limit its size.
    - Obviously, with larger pools of users and commands being run, this is not ideal.
    - Need to limit log size to a configurable size in KB
    - Need to setup logging of specific levels or higher ie WARN+ would only log warnings and more sever entries
- [ ] Enable countdown to sensitive command deletion
    - If permissions are granted outside of a DM with the bot, it will automatically delete the message requesting the permissions after five seconds.
    - Add a countdown timer (or option to delete immediately) via emoji reactions on the message
    - Granting permissions outside of DMs is easier, as it allows for mentioning the users without having to copy their IDs
- [ ] Rewrite the `$help` command to be more presentable.
    - Currently, the help command is the default help command included with discord.py
    - While useful, I would like to pretty it up a bit or reformat it
- [ ] Flask Interface?
    - This may be split off into another project, instead of combining the flask interface with the discord bot.