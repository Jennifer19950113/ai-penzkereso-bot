const botHandler = require('../../src/index.js');

module.exports = async (req, res) => {
  if (req.method === 'POST') {
    try {
      const update = req.body;
      
      // Handle Telegram webhook update
      await botHandler(update);
      
      // Respond immediately with 200 OK
      res.status(200).json({ ok: true });
    } catch (error) {
      console.error('Webhook error:', error);
      res.status(200).json({ ok: true }); // Always return 200 to Telegram
    }
  } else if (req.method === 'GET') {
    // Health check endpoint
    res.status(200).json({ status: 'Bot webhook is running' });
  } else {
    res.status(405).json({ error: 'Method not allowed' });
  }
};
