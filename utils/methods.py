import discord


async def add_reactions(self, *emojis):

    for emoji in emojis:
        emoji = discord.message.convert_emoji_reaction(emoji)
        await self._state.http.add_reaction(self.channel.id, self.id, emoji)


def get_message(self, id):

    return self._state._get_message(id)


discord.Message.add_reactions = add_reactions
discord.abc.Messageable.get_message = get_message
