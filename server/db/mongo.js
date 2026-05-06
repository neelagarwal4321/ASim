const mongoose = require('mongoose');

async function connectMongo() {
  await mongoose.connect(process.env.MONGODB_URL);
}

module.exports = { connectMongo };
