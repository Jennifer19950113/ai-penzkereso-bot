const logger = require('../utils/logger');

const handleStart = async (ctx) => {
  try {
    const userId = ctx.from.id;
    const firstName = ctx.from.first_name || 'Felhasználó';

    logger.info(`Felhasználó ${userId} elindította a botot`);

    const startMessage = `Üdvözlünk, ${firstName}! 👋

🤖 Ez a Pénzkereső Bot segít valódi ügyfelek és munkalehetőségek keresésében.

💼 Ügyfélszerzés
🎨 Festési munkák
🧹 Takarítás
🏗️ Építőipari munkák
🚚 Költöztetés
💇 Hajfonás és hajhosszabbítás
💻 Online munkák

A /help paranccsal megnézheted, hogyan működik a bot.

Fontos: a bot nem garantál bevételt vagy automatikus profitot. A célja valódi munkalehetőségek és ügyfelek megtalálásának segítése.`;

    await ctx.reply(startMessage);
  } catch (error) {
    logger.error('Hiba a handleStart-ban:', error);
    await ctx.reply('Sajnos nem sikerült feldolgozni az indítási parancsot.');
  }
};

const handleHelp = async (ctx) => {
  try {
    const helpMessage = `📖 Hogyan működik a Pénzkereső Bot?

A bot célja, hogy segítsen munkalehetőségeket és valódi ügyfeleket keresni.

Elérhető területek:
💼 Ügyfélszerzés
🎨 Festés és felújítás
🧹 Takarítás
🏗️ Építőipari munkák
🚚 Költöztetés
💇 Hajfonás és hajhosszabbítás
💻 Online munkák

A következő lépésben a botot tovább lehet fejleszteni kategóriák, munkakeresés és érdeklődők adatainak kezelésére.

⚠️ A bot nem garantál bevételt és nem ígér automatikus profitot.

/start - Bot indítása
/help - Súgó megjelenítése`;

    logger.info(`Felhasználó ${ctx.from.id} segítséget kért`);
    await ctx.reply(helpMessage);
  } catch (error) {
    logger.error('Hiba a handleHelp-ben:', error);
    await ctx.reply('Sajnos nem sikerült feldolgozni a segítség parancsot.');
  }
};

module.exports = {
  handleStart,
  handleHelp
};
