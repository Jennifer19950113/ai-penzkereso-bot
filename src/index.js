require('dotenv').config();
const { Telegraf } = require('telegraf');
const logger = require('./utils/logger');
const { handleStart, handleHelp } = require('./handlers/commands');
const { handleMessage } = require('./handlers/messages');

const BOT_TOKEN = process.env.BOT_TOKEN;
const WEBHOOK_URL = process.env.WEBHOOK_URL;
const PORT = process.env.PORT || 3000;

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

// Determine mode based on environment
const isWebhookMode = WEBHOOK_URL && process.env.NODE_ENV === 'production';

if (isWebhookMode) {
  // Webhook mode for serverless environments
  logger.info('Starting bot in WEBHOOK mode');
  logger.info(`Webhook URL: ${WEBHOOK_URL}`);
  
  bot.telegram.setWebhook(WEBHOOK_URL).catch((err) => {
    logger.error('Failed to set webhook:', err);
  });
  
  // Export for serverless function handlers (AWS Lambda, Vercel, etc.)
  module.exports = async (update) => {
    try {
      logger.info('Received webhook update');
      await bot.handleUpdate(update);
    } catch (error) {
      logger.error('Error handling update:', error);
    }
  };
  
  logger.info('Bot ready for webhook updates');
} else {
  // Long polling mode for development or when webhook is not configured
  logger.info('Starting bot in LONG POLLING mode');
  
  // Process termination handlers
  process.once('SIGINT', () => {
    logger.info('Bot stopping (SIGINT)...');
    bot.stop('SIGINT');
  });

  process.once('SIGTERM', () => {
    logger.info('Bot stopping (SIGTERM)...');
    bot.stop('SIGTERM');
  });

  // Start the bot with long polling
  logger.info('Starting Telegram bot with long polling...');
  bot.launch();
  logger.info('Bot started successfully!');
}
