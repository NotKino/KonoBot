import ast
from collections import OrderedDict
import time
import typing

import discord
from discord.ext import commands


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


class SocketEvent(commands.Converter):
    # idk what to call this
    async def convert(self, ctx, argument):
        """Convert OPCode"""
        self._responses = ctx.cog._responses

        event = self._responses.get(int(argument))

        if event:
            return event

        raise Exception(
            f'invalid sequence number\nthere are {len(self._responses)} events in cache')


class SocketType(commands.Converter):
    async def convert(self, ctx, argument):

        if argument in ctx.bot._connection.parsers.keys():
            return argument

        raise Exception(
            'invalid event type')


class RawData(commands.Converter):
    async def convert(self, ctx, argument):

        try:
            return ast.literal_eval(argument)
        except SyntaxError:
            raise Exception(
                'Invalid raw data.'
            )


class Useful(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self._responses = OrderedDict()

    async def cog_command_error(self, ctx, error):

        if isinstance(error, (commands.ConversionError, commands.BadArgument)):
            await ctx.send(error.__cause__)
        elif isinstance(error, commands.CommandOnCooldown):
            if ctx.author.id == ctx.bot.owner_id:
                return await ctx.reinvoke()
            await ctx.send(error)
        else:
            raise error

    @commands.Cog.listener('on_socket_response')
    async def socket_listener(self, data):
        """Listen for socket events, add to cache"""
        if data['op'] != 0:
            return
        s = data.get('s')

        data['when'] = time.time()
        self._responses[s] = data

    async def find_type(self, ctx, object_id):

        bot = ctx.bot
        http = ctx.bot.http

        if not commands.IDConverter()._get_id_match(str(object_id)):
            return None

        # finds object type
        # if type is lower priority
        # we rely on cache

        object = bot.get_channel(object_id)
        if object:
            return await http.get_channel(object.id)
        object = bot.get_emoji(object_id)
        if object:
            return await http.get_custom_emoji(object.guild.id, object.id),
        object = ctx.get_message(object_id)
        if object:
            return await http.get_message(object.channel.id, object.id)
        object = bot.get_user(object_id)
        if object:
            return await http.get_user(object.id)

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

    def get_type(self, ctx, data):

        # this will break with some types
        # too lazy to fix that
        state = ctx.bot._connection

        if data.get('last_message_id') is not None:
            return discord.TextChannel(state=state, guild=ctx.guild, data=data)
        elif data.get('bitrate') is not None:
            return discord.VoiceChannel(state=state, guild=ctx.guild, data=data)
        elif data.get('require_colons') is not None:
            return discord.Emoji(state=state, guild=ctx.guild, data=data)
        elif data.get('nick') is not None:
            return discord.Member(data=data, guild=ctx.guild, state=state)
        elif data.get('username') is not None:
            return discord.User(state=state, data=data)
        elif data.get('content') is not None:
            return discord.Message(state=state, channel=ctx.channel, data=data)
        elif data.get('emoji') is not None:
            pass

        return None

    @commands.group(
        aliases=('ss', 'show ss',), help='Shows most recent socket event statistics.',
        invoke_without_command=True, case_insensitive=True,
    )
    async def socketstats(self, ctx, response: SocketEvent = None):
        # horrid

        if not response:
            try:
                response = self._responses[list(self._responses)[-2]]
            except IndexError:
                # this should never happen
                return await ctx.send('no events in cache')

        elif response in ('recent', 'r'):
            stuff, loop = str(), int()
            for event in list(self._responses)[::-1]:
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

    @socketstats.command(
        help='Constructs a discord object from most recent socket event statistics.', aliases=('sc', 'c')
    )
    async def socket_construct(self, ctx, *, response: SocketEvent = None):

        if not response:
            try:
                response = self._responses[list(self._responses)[-2]]
            except IndexError:
                return await ctx.send('No events in cache')

        data = response.get('d')

        if not data:
            return await ctx.send('No data from this event.')

        async with ctx.typing():
            type = self.get_type(ctx, data)
        if type is None:
            return await ctx.send(f'Could not construct for type: {response["t"]}')
        await ctx.send(repr(type))

    @socketstats.command(
        help='Shows recent events with specified type.', aliases=('s',)
    )
    async def show(self, ctx, type: SocketType):

        found = list()

        for seq, data in self._responses.items():
            if data['t'] == type:
                found.append(seq)

        output = f'```\n{type}: {", ".join(str(seq) for seq in found)}\n```'

        if len(output) > 2000:
            output = f'```\n{type}: {", ".join(str(seq) for seq in found[-20])}\n```'

        await ctx.send(output)

    @commands.group(
        help='Shows raw data of different discord objects.', invoke_without_command=True, case_insensitive=True,
    )
    @commands.guild_only()
    async def raw(self, ctx):
        await ctx.send_help(ctx.command)

    @raw.command(
        aliases=('m', 'msg',), help='Retrives raw data of a message.\n The Message\'s ID must be passed.',
    )
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def message(self, ctx, message_id: int, channel_id: typing.Optional[commands.TextChannelConverter]):
        if not channel_id:
            channel_id = ctx.channel.id

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
        aliases=('f', 'search', 'get',), help='Retrives raw data of a channel/emoji/message/user object.\nThe object\'s ID must be passed.',
    )
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def find(self, ctx, object_id: int):

        async with ctx.typing():
            data = await self.find_type(ctx, object_id)
        if not data:
            return await ctx.send(f'``{object_id}``: Not found.')
        await ctx.send(discord.utils.escape_markdown(str(data)))

    @raw.command(
        aliases=('s', 'sock',), help='Retrives raw data of a websocket event.\nThe event\'s sequence may be passed'
    )
    async def socket(self, ctx, *, response: SocketEvent = None):

        if not response:
            try:
                response = self._responses[list(self._responses)[-2]]
            except IndexError:
                return await ctx.send('No events in cache')

        await ctx.send(discord.utils.escape_markdown(response))

    @commands.group(
        invoke_without_command=True, case_insensitive=True,
        aliases=('c', 'con',), help='Constructs a discord object from raw data.',
    )
    async def construct(self, ctx, *, data: RawData):

        async with ctx.typing():
            type = self.get_type(ctx, data)
        if type is None:
            return await ctx.send('Invalid data.')
        await ctx.send(repr(type))

    @construct.command(
        hidden=True, name='dispatch', aliases=('d',)
    )
    @commands.is_owner()
    async def _dispatch(self, ctx, *, data: RawData):
        async with ctx.typing():
            message = self.get_type(ctx, data)
        if message is None or not isinstance(message, discord.Message):
            return await ctx.send('Invalid data.')
        ctx.bot.dispatch('message', message)
        await ctx.message.add_reaction('\U00002705')

    @commands.command(aliases=('src',))
    async def source(self, ctx):
        await ctx.send('<https://github.com/NotKino/KonoBot>')


def setup(bot):
    bot.add_cog(Useful(bot))
