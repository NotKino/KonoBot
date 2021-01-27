import discord
from discord.ext import commands

import datetime
import time


class SocketTime:
    def __init__(self, time):
        """Convert time to h, m, and s format."""
        try:
            time = int(time)
        except ValueError:
            raise commands.BadArgument(f'{time} is not an integer.')

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
        self._response_cache = ctx.bot.cogs['useful']._response_cache

        if argument in ('recent', 'r'):
            return argument

        for response in self._response_cache:

            if argument == str(response['s']):
                return self._response_cache[int(argument) - 1]

        raise Exception(
            f'invalid sequence number\nthere are {len(self._response_cache)} events in cache')


class useful(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self._response_cache = list()

    async def cog_command_error(self, ctx, error):

        if isinstance(error, commands.errors.ConversionError):
            await ctx.send(error.original)
        else:
            raise error

    @commands.Cog.listener('on_socket_response')
    async def socket_listener(self, message):
        """Listen for socket events, append to cache"""
        if message['op'] != 0:
            return
        message['when'] = time.time()
        self._response_cache.append(message)

    @commands.command(
        aliases=['ss', 'show ss'], help='Shows most recent socket event statistics'
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

        if op != 0:
            keys = None
        else:
            keys = len(response['d'].keys())

        embed = discord.Embed(
            title=f'**{event}**',
            description=f'**OPCode -** ``{op}``\n**Sequence -** ``{seq}``\n**When -** ``{when} ago``\n**Data Keys -** ``{keys}``',
        )

        await ctx.send(embed=embed)

    @commands.command()
    async def source(self, ctx):
        """Shows bot's source code"""
        await ctx.send('https://github.com/NotKino/KonoBot')


def setup(bot):
    bot.add_cog(useful(bot))
