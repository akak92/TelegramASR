// init-mongo.js
// Inicializa la base de datos MedicalASR con la colección transcriptions
// e índices optimizados para las consultas más habituales.

db = db.getSiblingDB('MedicalASR');

db.createCollection('transcriptions');

// Índice por usuario para listar el historial de un médico
db.transcriptions.createIndex({ "telegram_user_id": 1 });

// Índice de fecha descendente para recuperar los registros más recientes
db.transcriptions.createIndex({ "created_at": -1 });

// Índice por estado para filtrar jobs pendientes/completados
db.transcriptions.createIndex({ "status": 1 });

print("✅ Base de datos 'MedicalASR' inicializada correctamente");
print("✅ Colección 'transcriptions' creada");
print("✅ Índices creados: telegram_user_id, created_at, status");
