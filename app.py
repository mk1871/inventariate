<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mi Primera Aplicación Flask</title>
</head>
<body>
    <h1>¡Hola, Mundo! Bienvenido a tu primera app Flask.</h1>
    <h2>Cargar archivo de inventario</h2>
    <form action="/procesar" method="POST" enctype="multipart/form-data">
        <label for="archivo">Selecciona un archivo de Excel:</label>
        <input type="file" id="archivo" name="archivo" accept=".xlsx" required>
        <button type="submit">Subir archivo</button>
    </form>
</body>
</html>
