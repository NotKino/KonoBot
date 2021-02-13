import discord
import time

def get_member(self, member_id):

    for guild in self.guilds:
        member = guild.get_member(member_id)
        if member:
            return member
            

def get_message(self, message_id):

    return self._connection._get_message(message_id)


async def latency(self):

    lat = time.perf_counter()
    await self.trigger_typing()  # not sure if /users/@me would be better
    return time.perf_counter() - lat

discord.Client.get_member = get_member
discord.Client.get_message = get_message
discord.abc.Messageable.latency = latency
