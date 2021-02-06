import discord


def get_message(self, id):

    return self._state._get_message(id)


discord.abc.Messageable.get_message = get_message
