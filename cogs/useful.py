import discord
from discord.ext import commands

import datetime
import time

import typing


class SocketTime:
    def __init__(self, time):
        """Convert time to d, h, m, and s format."""
        try:
            time = int(time)
        except ValueError:
            raise commands.BadArgument(f'{time} is not a valid time.')

        if time >= 86400:
            # lol
            self.time = str(int(time / 86400)) + 'd'
        elif time >= 3600:
            self.time = str(int(time / 3600)) + 'h'
        elif time >= 60:
            self.time = str(int(time / 60)) + 'm'
        else:
            self.time = str(time) + 's'

    @classmethod
    def convert(cls, time):
        return cls(time)


class DiscordDispatch(commands.Converter):
    # idk what to call this
    async def convert(self, ctx, argument):
        """Convert OPCode"""
        self._response_cache = ctx.cog._response_cache

        if argument in ('recent', 'r'):
            return argument

        for response in self._response_cache:

            if argument == str(response['s']):
                return self._response_cache[int(argument) - 1]

        raise Exception(
            f'invalid sequence number\nthere are {len(self._response_cache)} events in cache')


class Useful(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self._response_cache = list()

    def _get_obj_channel(self, obj):
        if hasattr(obj, 'channel'):
            return obj.channel.id
        return None

    def _get_obj_guild(self, obj):
        if hasattr(obj, 'guild'):
            return obj.guild.id
        return None

    async def find_type(self, ctx, object_id):

        bot = ctx.bot
        http = ctx.bot.http

        if not commands.IDConverter()._get_id_match(str(object_id)):
            return None

        async def fetch_type(object):

            types = {
                discord.abc.GuildChannel: http.get_channel(object.id),
                discord.Emoji: http.get_custom_emoji(self._get_obj_guild(object), object.id),
                discord.Message: http.get_message(self._get_obj_channel(object), object.id),
                discord.User: http.get_user(object.id),
            }
            if isinstance(object, discord.abc.GuildChannel):
                return await types.get(discord.abc.GuildChannel)

            return await types.get(type(object))

        # finds object type
        # if type is lower priority
        # we rely on cache

        object = bot.get_channel(object_id)
        if object:
            return await fetch_type(object)
        object = bot.get_emoji(object_id)
        if object:
            return await fetch_type(object)
        object = bot.get_message(object_id)
        if object:
            return await fetch_type(object)
        object = bot.get_user(object_id)
        if object:
            return await fetch_type(object)

        try:
            return await http.get_message(ctx.channel.id, object_id)
        except discord.NotFound:
            pass
        try:
            return await http.get_channel(object_id)
        except discord.NotFound:
            pass
        try:
            return await http.get_user(object_id)
        except discord.NotFound:
            pass

        return None

    async def cog_command_error(self, ctx, error):

        if isinstance(error, (commands.ConversionError, commands.BadArgument)):
            await ctx.send(error.__cause__)
        elif isinstance(error, commands.CommandOnCooldown):
            if ctx.author.id == ctx.bot.owner_id:
                return await ctx.reinvoke()
            await ctx.send(error)
        else:
            raise error

    @commands.Cog.listener('on_disconnect')
    async def cache_clear(self):
        """Clear cache if ws discconnect."""
        # Disconnect might fuck up our sequence
        self._response_cache = list()

    @commands.Cog.listener('on_socket_response')
    async def socket_listener(self, message):
        """Listen for socket events, append to cache"""
        if message['op'] != 0:
            return
        message['when'] = time.time()
        self._response_cache.append(message)

    @commands.command(
        aliases=('ss', 'show ss',), help='Shows most recent socket event statistics.'
    )
    async def socketstats(self, ctx, response: DiscordDispatch = None):
        # horrid

        if response is None:
            try:
                response = self._response_cache[-2]
            except IndexError:
                # this should never happen
                await ctx.send('no events in cache')

        elif response in ('recent', 'r'):
            stuff, loop = str(), int()
            for event in self._response_cache[::-1]:
                if loop == 6:
                    break
                else:
                    stuff += f"\n{event['t']} : {event['s']}"
                    loop += 1

            embed = discord.Embed(
                description=f'```\n{stuff}```'
            )
            return await ctx.send(embed=embed)

        seq = response.get('s')
        op = response.get('op')
        event = response.get('t')
        when = SocketTime.convert(time.time() - response['when']).time
        keys = len(response['d'].keys())

        embed = discord.Embed(
            title=f'**{event}**',
            description=f'**OPCode -** ``{op}``\n**Sequence -** ``{seq}``\n**When -** ``{when} ago``\n**Data Keys -** ``{keys}``',
        )

        await ctx.send(embed=embed)

    @commands.group(
        help='Shows raw data of different discord objects.', invoke_without_command=True, case_insensitive=True
    )
    async def raw(self, ctx):
        await ctx.send_help(ctx.command)

    @raw.command(
        aliases=('m', 'msg',), help='Retrives raw data of a message.\n The Message\'s ID must be passed.',
    )
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def message(self, ctx, message_id: int, channel_id: typing.Optional[commands.TextChannelConverter]):
        if not channel_id:
            channel_id = ctx.channel
        channel_id = channel_id.id

        try:
            data = await ctx.bot.http.get_message(channel_id, message_id)
        except discord.NotFound:
            await ctx.send('not found')
        except discord.HTTPException:
            await ctx.send('no lol')
        else:
            await ctx.send(discord.utils.escape_markdown(str(data)))

    @raw.command(
        aliases=('u',), help='Retrives raw data of a user.\nThe user\'s ID must be passed.',
    )
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def user(self, ctx, user_id: typing.Optional[int]):
        if not user_id:
            user_id = ctx.author.id

        try:
            data = await ctx.bot.http.get_user(user_id)
        except discord.NotFound:
            await ctx.send('not found')
        except discord.HTTPException as exc:
            await ctx.send(f'no lol: {exc}')
        else:
            await ctx.send(discord.utils.escape_markdown(str(data)))

    @raw.command(
        aliases=('mem',), help='Retrives raw data of a member.\nSimilar to user\nThe member\'s ID must be passed.',
    )
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def member(self, ctx, member_id: typing.Optional[int]):
        if not member_id:
            member_id = ctx.author.id
        guild_id = ctx.guild.id

        try:
            data = await ctx.bot.http.get_member(guild_id, member_id)
        except discord.NotFound:
            await ctx.send('not found')
        except discord.HTTPException as exc:
            await ctx.send(f'no lol: {exc}')
        else:
            await ctx.send(discord.utils.escape_markdown(str(data)))

    @raw.command(
        aliases=('c', 'chan',), help='Retrives raw data of a channel.\nThe channel\'s ID must be passed.',
    )
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def channel(self, ctx, channel_id: typing.Optional[int]):
        if not channel_id:
            channel_id = ctx.channel.id

        try:
            data = await ctx.bot.http.get_channel(channel_id)
        except discord.NotFound:
            await ctx.send('not found')
        except discord.HTTPException as exc:
            await ctx.send(f'no lol: {exc}')
        else:
            await ctx.send(discord.utils.escape_markdown(str(data)))

    @raw.command(
        aliases=('e', 'emo',), help='Retrives raw data of a custom emoji.\nThe emoji\'s ID must be passed.',
    )
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def emoji(self, ctx, emoji_id: typing.Optional[int]):
        guild_id = ctx.guild.id

        try:
            data = await ctx.bot.http.get_custom_emoji(guild_id, emoji_id)
        except discord.NotFound:
            await ctx.send('not found')
        except discord.HTTPException as exc:
            await ctx.send(f'no lol: {exc}')
        else:
            await ctx.send(discord.utils.escape_markdown(str(data)))

    @raw.command(
        aliases=('f', 'search', 's',), help='Retrives raw data of a channel/emoji/message/user object.\nThe object\'s ID must be passed.',
    )
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def find(self, ctx, object_id: int):

        async with ctx.typing():
            data = await self.find_type(ctx, object_id)
        if not data:
            return await ctx.send(f'``{object_id}``: Not found.')
        await ctx.send(discord.utils.escape_markdown(str(data)))

    @commands.command(aliases=('src',))
    async def source(self, ctx):
        await ctx.send('<https://github.com/NotKino/KonoBot>')


def setup(bot):
    bot.add_cog(Useful(bot))
