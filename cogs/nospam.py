from discord.ext import commands
from discord.ext.commands import CooldownMapping


class NoSpam(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.spam = CooldownMapping.from_cooldown(
            4.0, 3.0, commands.BucketType.user,
        )

    @commands.Cog.listener('on_message')
    async def nospam(self, message):
        """Stop bot from spamming"""
        if message.author == self.bot.user:
            self.bucket = self.spam.get_bucket(message)
            updated = self.bucket.update_rate_limit()
            if updated:
                print('Bot is spamming; logging out.')
                await self.bot.logout()

        elif message.author.id == self.bot.owner_id:
            # We want to reset if debugging
            try:
            	self.bucket.reset()
            except AttributeError:
            	pass

def setup(bot):
    bot.add_cog(NoSpam(bot))
