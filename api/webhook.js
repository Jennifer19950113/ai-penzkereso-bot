require('dotenv').config();
const { Telegraf } = require('telegraf');
const logger = require('../../src/utils/logger');
const { handleStart, handleHelp } = require('../../src/handlers/commands');
const { handleMessage } = require('../../src/handlers/messages');

// Initialize bot instance for webhook processing
let bot = null;

function initializeBot() {
  const BOT_TOKEN = process.env.BOT_TOKEN;
  
  if (!BOT_TOKEN) {
    logger.error('BOT_TOKEN environment variable is not set!');
    return null;
  }

  bot = new Telegraf(BOT_TOKEN);

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

  return bot;
}

// Vercel serverless function handler
module.exports = async (req, res) => {
  try {
    // Initialize bot on first request
    if (!bot) {
      bot = initializeBot();
    }

    if (!bot) {
      logger.error('Bot failed to initialize');
      return res.status(500).json({ error: 'Bot not configured' });
    }

    if (req.method === 'POST') {
      const update = req.body;

      logger.info('Received webhook update from Telegram');

      // Process Telegram webhook update
      await bot.handleUpdate(update);

      // Always respond with 200 OK to Telegram
      res.status(200).json({ ok: true });
    } else if (req.method === 'GET') {
      // Health check endpoint
      res.status(200).json({ status: 'Bot webhook is running' });
    } else {
      res.status(405).json({ error: 'Method not allowed' });
    }
  } catch (error) {
    logger.error('Webhook processing error:', error);
    // Always return 200 to Telegram even on error
    res.status(200).json({ ok: true });
  }
};
