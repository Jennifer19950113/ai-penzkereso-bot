require('dotenv').config();
const { Telegraf } = require('telegraf');
const logger = require('./utils/logger');
const { handleStart, handleHelp } = require('./handlers/commands');
const { handleMessage } = require('./handlers/messages');

const BOT_TOKEN = process.env.BOT_TOKEN;

if (!BOT_TOKEN) {
  logger.error('BOT_TOKEN environment variable is not set!');
  process.exit(1);
}

const bot = new Telegraf(BOT_TOKEN);

// Command handlers
bot.command('start', handleStart);
bot.command('help', handleHelp);

// Message handlers
bot.on('text', handleMessage);

// Error handling
bot.catch((err, ctx) => {
  logger.error('Bot error:', err);
  ctx.reply('Sajnos hiba lépett fel. Kérlek, próbáld újra később.');
});

// Process termination handlers
process.once('SIGINT', () => {
  logger.info('Bot stopping (SIGINT)...');
  bot.stop('SIGINT');
});

process.once('SIGTERM', () => {
  logger.info('Bot stopping (SIGTERM)...');
  bot.stop('SIGTERM');
});

// Start the bot
logger.info('Starting Telegram bot...');
bot.launch();
logger.info('Bot started successfully!');
