const logger = require('../utils/logger');

const handleMessage = async (ctx) => {
  try {
    const userId = ctx.from.id;
    const userMessage = ctx.message.text;

    logger.info(`Felhasználó ${userId} üzenete: ${userMessage}`);

    // Show typing indicator
    await ctx.sendChatAction('typing');

    const response = `Köszönöm az üzenetered! 🙏

A Pénzkereső Bot segít valódi ügyfeleket és munkalehetőségeket keresni. A botot arra terveztük, hogy támogatnod a munkaalkalmak megtalálásában különböző területeken.

Elérhető munkakategóriák:

💼 *Ügyfélszerzés*
🎨 *Festési munkák*
🧹 *Takarítás*
🏗️ *Építőipari munkák*
🚚 *Költöztetés*
💇 *Hajfonás és hajhosszabbítás*
💻 *Online munkák*

❓ *Melyik kategória érdekel téged a legjobban?*

Válaszolj az egyik fenti kategóriával, és segítségünkre lehetünk abban, hogy valódi ügyfélkört építs fel.

⚠️ *Fontos:* A bot nem garantál bevételt vagy automatikus profitot. A célja a munkaalkalmak és ügyfelek megtalálásában való segítés.

További információért használd a /help parancsot.`;

    await ctx.reply(response);
  } catch (error) {
    logger.error('Hiba a handleMessage-ben:', error);
    await ctx.reply('Sajnos nem sikerült feldolgozni az üzenetedet. Próbáld újra később.');
  }
};

module.exports = {
  handleMessage
};
