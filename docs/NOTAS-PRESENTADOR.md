# Delivery Atlas: chuleta bilingüe

Guion de la presentación simplificada. Seis diapositivas, unos cinco minutos.

Presentad en inglés. El español ayuda a entender y ensayar. La **negrita negra** marca lo esencial. Los tiempos son orientativos y no están medidos en un ensayo.

PDF: [chuleta EN/ES](../output/pdf/Delivery-Atlas-Cheat-Sheet-Simple-EN-ES.pdf).

## 1. Delivery Atlas

**Tiempo:** 0:00 - 0:30.

**Qué señalar:** Presentad la idea y señalad qué funciona hoy y qué construiréis después.

### English - what to say

Our project is **Delivery Atlas**, a fictional food delivery app inspired by Uber Eats and Glovo. We want to **record user actions and show them in a dashboard**.

We already have a **working ClickHouse lab with large public datasets**. The delivery app is our next step.

**Next:** First, what is ClickHouse?

### Español - para entenderlo

Nuestro proyecto es **Delivery Atlas**, una aplicación ficticia de reparto inspirada en Uber Eats y Glovo. Queremos **registrar las acciones de los usuarios y mostrarlas en un dashboard**.

Ya tenemos un **entorno de ClickHouse funcionando con grandes datasets públicos**. El siguiente paso es construir la aplicación de reparto.

**Transición:** Primero, ¿qué es ClickHouse?

## 2. What is ClickHouse?

**Tiempo:** 0:30 - 1:10.

**Qué señalar:** Explicad las tres ideas de la izquierda. La tabla es solo un ejemplo sencillo.

### English - what to say

**ClickHouse is a database designed to analyse large amounts of data**. It stores information by columns, so a query can read the fields it needs.

We use **SQL to count events and filter results**, for example by date or city. This makes it a good fit for a dashboard with millions of records.

We run our current database in Docker on one node.

**Next:** These are the datasets we use to test it.

### Español - para entenderlo

**ClickHouse es una base de datos diseñada para analizar grandes cantidades de datos**. Guarda la información por columnas, de modo que una consulta puede leer los campos que necesita.

Usamos **SQL para contar eventos y filtrar resultados**, por ejemplo por fecha o ciudad. Por eso encaja con un dashboard que trabaja con millones de registros.

Nuestra base de datos actual funciona en Docker, en un solo nodo.

**Transición:** Estos son los datasets que usamos para probarla.

## 3. Our data sources

**Tiempo:** 1:10 - 2:00.

**Qué señalar:** Señalad los datos públicos y después la actividad ficticia que proponéis generar.

### English - what to say

Our main datasets are **OTTO and REES46**, with about **628 million historical e-commerce events** in total. They come from different populations, so we keep them separate.

**Ele.me adds food recommendation samples**. Glovo adds a product catalogue, including products from Spain. These records have different meanings.

For our own app, we propose **simulated food delivery actions**, such as opening a restaurant or adding a product to the cart. We will clearly label simulated data.

**Next:** Next, this is how we propose to collect and organise app events.

### Español - para entenderlo

Los principales datasets son **OTTO y REES46**, con unos **628 millones de eventos históricos de comercio electrónico** en total. Proceden de poblaciones diferentes, por eso los mantenemos separados.

**Ele.me aporta muestras de recomendaciones de comida**. Glovo aporta un catálogo de productos, incluidos productos de España. Estos registros tienen significados distintos.

Para nuestra propia aplicación, proponemos **acciones simuladas de reparto**, como abrir un restaurante o añadir un producto al carrito. Identificaremos claramente los datos simulados.

**Transición:** Ahora veremos cómo proponemos recoger y organizar los eventos de la aplicación.

## 4. Proposed data flow and schema

**Tiempo:** 2:00 - 3:10.

**Qué señalar:** Recorred las flechas y explicad la tabla: una acción, una fila. Aclarad que es una propuesta.

### English - what to say

The proposed flow is simple: **the app produces an event, Python checks it, and ClickHouse stores it**. The dashboard will query the results through Python.

**One row represents one action**. We record an event ID, the session, the time, the action, the city and the origin of the data. For example, a simulated user opens a restaurant in Madrid.

We plan to **group data by month and create daily summaries**. The SQL design exists, but this app integration is still a proposal.

**Next:** We have already tested why daily summaries can help.

### Español - para entenderlo

El recorrido propuesto es sencillo: **la aplicación genera un evento, Python lo comprueba y ClickHouse lo guarda**. El dashboard consultará los resultados a través de Python.

**Cada fila representa una acción**. Guardamos un identificador del evento, la sesión, la hora, la acción, la ciudad y el origen de los datos. Por ejemplo, un usuario simulado abre un restaurante en Madrid.

Queremos **agrupar los datos por mes y crear resúmenes diarios**. El diseño SQL existe, pero esta integración con la aplicación sigue siendo una propuesta.

**Transición:** Ya hemos probado por qué los resúmenes diarios pueden ayudar.

## 5. A faster dashboard

**Tiempo:** 3:10 - 4:00.

**Qué señalar:** Señalad las barras: 5,89 segundos frente a 0,21. El resultado es el mismo.

### English - what to say

We tested **counting OTTO events by day and type**. Reading about **217 million events** took **5.89 seconds**.

Reading a daily summary took **0.21 seconds**, with **the same answer**. That was **about 28 times faster in this test on our computer**.

Both queries used ClickHouse. This shows how daily summaries can help the dashboard respond faster.

**Next:** Finally, this is what works today and what comes next.

### Español - para entenderlo

Probamos a **contar los eventos de OTTO por día y tipo**. Leer unos **217 millones de eventos** tardó **5,89 segundos**.

Consultar un resumen diario tardó **0,21 segundos**, con **el mismo resultado**. Fue **casi 28 veces más rápido en esta prueba, en nuestro ordenador**.

Las dos consultas usaron ClickHouse. Esto muestra cómo los resúmenes diarios pueden ayudar a que el dashboard responda más rápido.

**Transición:** Para terminar, esto es lo que funciona hoy y lo que haremos después.

## 6. Current progress and next steps

**Tiempo:** 4:00 - 5:00.

**Qué señalar:** Primero lo que ya funciona. Después lo que vais a construir y comprobar.

### English - what to say

Today, **ClickHouse, the public datasets and the dashboard already work**. We also have a measured query comparison.

Next, we will **connect the delivery mini app and generate simulated activity**. We will check that the dashboard shows new actions correctly.

We also need to **avoid counting repeated requests twice**, test many actions arriving at once, and check that another person can run the project. Our current setup uses one node, so failure recovery still needs testing.

**Next:** Thank you. We can show the dashboard or answer your questions.

### Español - para entenderlo

Actualmente, **ClickHouse, los datasets públicos y el dashboard ya funcionan**. También tenemos una comparación de consultas medida.

Después vamos a **conectar la pequeña aplicación de reparto y generar actividad simulada**. Comprobaremos que el dashboard muestre correctamente las nuevas acciones.

También necesitamos **evitar contar dos veces las peticiones repetidas**, probar muchas acciones llegando a la vez y comprobar que otra persona pueda ejecutar el proyecto. El entorno actual usa un solo nodo, por lo que aún debemos probar la recuperación ante fallos.

**Transición:** Gracias. Podemos enseñar el dashboard o responder a vuestras preguntas.
