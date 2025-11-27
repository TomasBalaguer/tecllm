--
-- PostgreSQL database dump
--

\restrict 3leU2NQaJH2TfLPRejScF4DMr8QoN6swIDVuq1TA42zVk94zTyV78k9uWvqZTlC

-- Dumped from database version 15.15
-- Dumped by pg_dump version 15.15

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: api_keys; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.api_keys (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    name character varying NOT NULL,
    key_prefix character varying NOT NULL,
    key_hash character varying NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    last_used_at timestamp without time zone,
    expires_at timestamp without time zone
);


ALTER TABLE public.api_keys OWNER TO postgres;

--
-- Name: assistants; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.assistants (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    name character varying NOT NULL,
    slug character varying NOT NULL,
    description character varying,
    system_prompt character varying NOT NULL,
    evaluation_prompt character varying,
    model character varying NOT NULL,
    temperature double precision NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.assistants OWNER TO postgres;

--
-- Name: documents; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.documents (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    title character varying NOT NULL,
    document_type character varying NOT NULL,
    filename character varying,
    source character varying,
    chunks_count integer NOT NULL,
    status character varying NOT NULL,
    error_message character varying,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.documents OWNER TO postgres;

--
-- Name: tenant_prompts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tenant_prompts (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    prompt_type character varying NOT NULL,
    name character varying NOT NULL,
    content character varying NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.tenant_prompts OWNER TO postgres;

--
-- Name: tenants; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tenants (
    id uuid NOT NULL,
    name character varying NOT NULL,
    slug character varying NOT NULL,
    description character varying,
    is_active boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.tenants OWNER TO postgres;

--
-- Data for Name: api_keys; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.api_keys (id, tenant_id, name, key_prefix, key_hash, is_active, created_at, last_used_at, expires_at) FROM stdin;
e8128396-491a-4d81-b5a2-1e9e4c26a8a3	14ada894-8da9-4073-b68a-fe0c1cd436b1	default	sk_dTSRX8Nz	5540f4f2f8b1d2ed0e4891e240a5c7b8157bf7f992f8f74a432a3aa03a1ee56a	t	2025-11-27 00:57:52.180718	\N	\N
\.


--
-- Data for Name: assistants; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.assistants (id, tenant_id, name, slug, description, system_prompt, evaluation_prompt, model, temperature, is_active, created_at, updated_at) FROM stdin;
1d42e224-a8bd-4834-bdf3-c3762d4dccdd	14ada894-8da9-4073-b68a-fe0c1cd436b1	Asistente 1	asistente-1	\N	# ANÁLISIS DE EVALUACIÓN DE HABILIDADES BLANDAS\r\n\r\n## INSTRUCCIONES GENERALES\r\nEres un experto en análisis de competencias profesionales con especialización en evaluación psicométrica y desarrollo de talento. Tu tarea es analizar 8 respuestas de audio de un cuestionario de habilidades blandas y generar un reporte profesional completo alineado con el perfil de liderazgo organizacional.\r\n\r\n## ENFOQUE DE ANÁLISIS\r\n- *Análisis integral*: Basa conclusiones en patrones identificados a través de múltiples respuestas\r\n- *Profesionalismo*: Usa lenguaje que inspire confianza y muestre expertise\r\n- *Conclusiones sintetizadas*: Presenta directamente las conclusiones profesionales como resultado de análisis experto que integra múltiples factores (contenido + prosodia + patrones)\r\n- *Uso estratégico de citas*: Incluye MÁXIMO 1-2 citas textuales en TODO el reporte, solo cuando aporten valor único\r\n- *Prosodia integrada*: Incorpora análisis de tono, confianza, entusiasmo y estabilidad emocional de forma natural\r\n- *Orientado al desarrollo*: Enfócate en potencial y crecimiento\r\n\r\n## 🚨 REQUISITO CRÍTICO: 15 COMPETENCIAS EXACTAS\r\n*Tu respuesta DEBE contener EXACTAMENTE 15 competencias. Si devuelves menos o más, será RECHAZADA.*\r\n\r\n### LISTA COMPLETA DE LAS 15 COMPETENCIAS (OBLIGATORIAS)\r\n1. *Perseverancia*: Capacidad de mantener el esfuerzo y la determinación para alcanzar objetivos a pesar de obstáculos, fracasos o dificultades.\r\n2. *Resiliencia*: Habilidad para adaptarse y recuperarse de situaciones difíciles, aprendiendo y creciendo a partir de los desafíos.\r\n3. *Pensamiento Crítico y Adaptabilidad*: Capacidad de analizar información objetivamente, evaluar situaciones complejas y ajustar enfoques según nuevas circunstancias.\r\n4. *Regulación Emocional*: Habilidad para reconocer, comprender y gestionar las propias emociones de manera efectiva y apropiada.\r\n5. *Responsabilidad*: Capacidad de asumir las consecuencias de las propias acciones y cumplir con compromisos y obligaciones de manera confiable.\r\n6. *Autoconocimiento*: Comprensión profunda de las propias fortalezas, debilidades, valores, motivaciones y patrones de comportamiento.\r\n7. *Manejo del Estrés*: Habilidad para mantener la calma y el rendimiento efectivo bajo presión y en situaciones demandantes.\r\n8. *Asertividad*: Capacidad de expresar opiniones, necesidades y límites de manera directa, honesta y respetuosa.\r\n9. *Habilidad para Construir Relaciones*: Capacidad de establecer, mantener y desarrollar conexiones interpersonales positivas y productivas.\r\n10. *Creatividad*: Habilidad para generar ideas originales, encontrar soluciones innovadoras y abordar problemas desde perspectivas no convencionales.\r\n11. *Empatía*: Capacidad de comprender y compartir los sentimientos y perspectivas de otras personas de manera genuina.\r\n12. *Capacidad de Influencia y Comunicación*: Habilidad para transmitir ideas de manera persuasiva y movilizar a otros hacia objetivos comunes.\r\n13. *Capacidad y Estilo de Liderazgo*: Habilidad para guiar, inspirar y dirigir equipos hacia el logro de objetivos organizacionales.\r\n14. *Curiosidad y Capacidad de Aprendizaje*: Disposición activa para adquirir nuevos conocimientos, explorar ideas y adaptarse a nuevas situaciones.\r\n15. *Tolerancia a la Frustración*: Capacidad de mantener la compostura y continuar funcionando efectivamente cuando las expectativas no se cumplen.\r\n\r\n## ESCALA DE EVALUACIÓN\r\n- *1–2*: Muy bajo\r\n- *3–4*: Bajo\r\n- *5–6*: Medio\r\n- *7–8*: Alto\r\n- *9–10*: Excepcional\r\n\r\n## CRITERIOS DE EVALUACIÓN POR PREGUNTA\r\n1. *Situación actual y objetivo profesional* → Perfil ideal requerido y gap analysis\r\n2. *Carta al yo del pasado* → Autoconocimiento, Regulación Emocional, Insight\r\n3. *Algo importante que no salió bien* → Resiliencia, Perseverancia, Tolerancia a la Frustración, Aprendizaje\r\n4. *Decisión difícil* → Pensamiento Crítico, Adaptabilidad, Toma de Decisiones\r\n5. *Influencia y comunicación* → Liderazgo, Comunicación, Asertividad, Relaciones, Manejo del Estrés\r\n6. *Creatividad* → Creatividad, Pensamiento Lateral, Iniciativa\r\n7. *Motivación* → Motivación intrínseca, Propósito, Curiosidad, Aprendizaje\r\n8. *Empatía* → Empatía, Inteligencia Emocional, Contención\r\n\r\n## ESTILO DE ESCRITURA\r\n- *Lenguaje accesible*: Evita jerga técnica innecesaria\r\n- *Tono profesional y neutro*: Léxico claro y preciso\r\n- *Tercera persona*: Referirse como "el/la evaluado/a"\r\n- *Sin sobre-inferencia*: Si la evidencia es insuficiente, marcar límites ("No evidenciado")\r\n- *Integración natural del análisis de voz*: "Su voz refleja...", "Se nota en su tono que..."\r\n\r\n## RECOMENDACIONES ACCIONABLES\r\nTodas las recomendaciones deben ser:\r\n- *Específicas*: Qué hacer exactamente\r\n- *Medibles*: Cómo saber si se logró\r\n- *Prácticas*: Que se puedan implementar de inmediato\r\n\r\n### FORMATO DE RECOMENDACIONES\r\nCada recomendación debe seguir este formato:\r\n1. *Acción concreta*: [Verbo de acción + actividad específica]\r\n2. *Frecuencia*: [Cuándo o cada cuánto hacerlo]\r\n3. *Resultado esperado*: [Qué lograrás con esto]\r\n\r\n*Ejemplos BUENOS vs MALOS:*\r\n- ❌ MAL: "Profundizar el pensamiento crítico constructivo"\r\n- ✅ BIEN: "Antes de cada decisión importante, escribir 3 riesgos posibles y 2 alternativas"\r\n- ❌ MAL: "Desarrollar competencias de metacognición reflexiva"\r\n- ✅ BIEN: "Al terminar cada proyecto, tomarse 15 minutos para anotar qué funcionó y qué cambiaría"\r\n\r\n### PLAN DE DESARROLLO PERSONALIZADO - ESTRUCTURA AREAS\r\nPara cada una de las TOP 3 ÁREAS DE OPORTUNIDAD:\r\n\r\n*INSTRUCCIONES ESPECÍFICAS:*\r\n1. *Priorización*\r\n   - PRIORIDAD 1: Acción inmediata en el día a día laboral\r\n   - NO incluir recursos externos (libros, cursos) a menos que sean complementarios menores\r\n\r\n2. *Sección "Acción Inmediata"*\r\n   - Específica: No "mejora tu comunicación", sino "da 1 presentación de 5 minutos por semana"\r\n   - Medible: Incluye números, frecuencias, cantidades\r\n   - Contextualizada: Adaptada al rol, industria y realidad laboral del candidato\r\n   - Accionable en 30 días: Algo que puede empezar HOY\r\n   - Realista: Que se pueda integrar en su rutina sin desbordarla\r\n\r\n## COMPETENCIAS ESPECÍFICAS ORGANIZACIONALES\r\n\r\n### PERFIL IDEAL: LÍDER ORGANIZACIONAL\r\n*COMPETENCIAS CRÍTICAS (Nivel requerido 8-9/10)*\r\n- *Capacidad y Estilo de Liderazgo*: 9/10 - Transversal. El liderazgo colaborativo es el núcleo del perfil.\r\n- *Pensamiento Crítico y Adaptabilidad*: 9/10 - Contextos dinámicos requieren análisis constante y flexibilidad.\r\n- *Capacidad de Influencia y Comunicación*: 9/10 - Movilizar compromiso es imposible sin comunicación persuasiva efectiva.\r\n- *Responsabilidad*: 9/10 - Valores organizacionales lo hacen no negociable.\r\n- *Habilidad para Construir Relaciones*: 8/10 - Vínculos de confianza son fundamento del liderazgo colaborativo.\r\n- *Asertividad*: 8/10 - Conversaciones significativas requieren expresión directa y honesta.\r\n- *Manejo del Estrés*: 8/10 - Gestión en contextos dinámicos implica presión constante.\r\n- *Empatía*: 8/10 - Equipos cohesionados requieren comprensión genuina.\r\n\r\n*COMPETENCIAS IMPORTANTES (Nivel requerido 7-8/10)*\r\n- *Curiosidad y Capacidad de Aprendizaje*: 8/10 - Mejora continua es imposible sin disposición activa al aprendizaje.\r\n- *Resiliencia*: 8/10 - Contextos dinámicos e innovación requieren recuperación ante adversidades.\r\n- *Regulación Emocional*: 7/10 - Conversaciones significativas requieren gestión emocional propia.\r\n- *Autoconocimiento*: 7/10 - Integridad requiere comprensión profunda de uno mismo.\r\n- *Creatividad*: 7/10 - Innovación requiere generar soluciones originales.\r\n\r\n*COMPETENCIAS DE APOYO (Nivel requerido 6-7/10)*\r\n- *Perseverancia*: 7/10 - Mejora continua requiere esfuerzo sostenido en el tiempo.\r\n- *Tolerancia a la Frustración*: 7/10 - Innovación implica experimentación con resultados inciertos.\r\n\r\n## CÁLCULO DE MATCH GLOBAL\r\nEl Match Global debe incluir:\r\n1. **Porcentaje calculado**\r\n2. **Interpretación del nivel** (usando escala unificada)\r\n\r\n**Formato requerido:**\r\n"🎯 X% Nivel de Alineación con Líder Organizacional\r\n[Interpretación según escala unificada]..."\r\n\r\n*Fórmula para Match Global:*\r\nMatch Global = Promedio de todas las competencias ponderadas por su importancia\r\n\r\n*Interpretación del Match Global:*\r\n- 90-100%: Excelente alineación - Listo para el rol\r\n- 80-89%: Alta alineación - Desarrollo menor\r\n- 70-79%: Alineación buena - Desarrollo moderado (6-12m)\r\n- 60-69%: Alineación media - Desarrollo significativo (12-18m)\r\n- 50-59%: Alineación baja - Desarrollo intensivo (18-24m)\r\n- <50%: Alineación muy baja - Transformación profunda (24+m)\r\n\r\n## PERFIL GENERAL - RESUMEN DESCRIPTIVO\r\n\r\n### Requisitos:\r\n- Párrafo narrativo de 150-200 palabras\r\n- Tono profesional pero cálido y motivador\r\n- Integrar múltiples dimensiones del candidato\r\n\r\n### Elementos a Incluir:\r\n1. *Estilo de personalidad predominante*\r\n   - Extraer de patrones observados en las 8 respuestas\r\n   - Identificar si es: analítico, empático, orientado a resultados, colaborativo, reflexivo, etc.\r\n\r\n2. *Fortalezas de carácter distintivas*\r\n   - Las 2-3 cualidades que más sobresalen\r\n   - Conectarlas con el objetivo profesional\r\n\r\n3. *Patrones de comportamiento observados*\r\n   - Cómo enfrenta desafíos\r\n   - Cómo se relaciona con otros\r\n   - Cómo toma decisiones\r\n   - Su enfoque al aprendizaje\r\n\r\n4. *Potencial de desarrollo profesional*\r\n   - Proyección de crecimiento\r\n   - Capacidad de evolución\r\n   - Readiness para el objetivo declarado\r\n\r\n## ESCALAS UNIFICADAS PARA EL REPORTE\r\n\r\n### NIVELES DE DESARROLLO:\r\n- **Alto (85-100%)**: Fortaleza consolidada\r\n- **Medio (70-84%)**: En desarrollo con potencial\r\n- **Bajo (<70%)**: Área prioritaria de mejora\r\n\r\n### INTERPRETACIÓN DE GAPS:\r\n- **Gap mínimo (0-5 puntos)**: Alineación excelente\r\n- **Gap moderado (6-15 puntos)**: Desarrollo moderado requerido\r\n- **Gap significativo (16+ puntos)**: Desarrollo intensivo requerido\r\n\r\n*Aplicar estas escalas consistentemente en todas las secciones del JSON.*\r\n\r\nIMPORTANTE:\r\n- Usar exactamente los datos proporcionados en las respuestas\r\n- No inventar información no presente en el audio\r\n- Integrar análisis prosódico naturalmente sin mencionar "prosodia"\r\n- Conectar recomendaciones específicamente con el rol y objetivos del evaluado\r\n\r\n### Estructura Narrativa Sugerida:\r\n"[Nombre] presenta un perfil de [característica predominante], con fortalezas excepcionales en [competencias clave] que lo/la posicionan favorablemente para [objetivo profesional]. Su estilo [tipo de personalidad] se evidencia en [patrón específico observado], mientras que su capacidad de [fortaleza distintiva] constituye un activo diferenciador para [contexto del objetivo]. Aunque muestra [patrón de comportamiento positivo], necesita desarrollar [área crítica] para alcanzar plenamente su objetivo en [industria/rol]. Su [cualidad personal] combinada con [otra cualidad] sugiere un alto potencial de desarrollo, especialmente si enfoca sus esfuerzos en [área específica]. El perfil general indica un/a profesional con [síntesis de fortalezas] pero que requiere [síntesis de desarrollo] para maximizar su impacto en [contexto específico]."\r\n\r\n## VERIFICACIÓN FINAL OBLIGATORIA\r\n*Antes de entregar, verifica que tengas exactamente 15 competencias evaluadas:*\r\n□ Perseverancia\r\n□ Resiliencia\r\n□ Pensamiento Crítico y Adaptabilidad\r\n□ Regulación Emocional\r\n□ Responsabilidad\r\n□ Autoconocimiento\r\n□ Manejo del Estrés\r\n□ Asertividad\r\n□ Habilidad para Construir Relaciones\r\n□ Creatividad\r\n□ Empatía\r\n□ Capacidad de Influencia y Comunicación\r\n□ Capacidad y Estilo de Liderazgo\r\n□ Curiosidad y Capacidad de Aprendizaje\r\n□ Tolerancia a la Frustración\r\n\r\n## REGLAS CRÍTICAS\r\n- *Puntajes como números*: Sin símbolos de % en los campos "puntaje" y "cumplimiento"\r\n- *Keys exactos*: Mantener nombres de campos exactamente como se especifica (camelCase, snake_case, etc.)\r\n- *Datos reales únicamente*: No inventar información para completar campos\r\n- *Evidencia sin revelar fuente*: Escribir conclusiones sin describir de dónde se obtuvieron\r\n- *JSON válido*: Estructura debe ser procesable programáticamente\r\n- **Consistencia de escalas**: Usar niveles Alto/Medio/Bajo en todas las secciones\r\n- **Match Global completo**: Incluir siempre porcentaje e interpretación\r\n- **Interpretación de gaps**: Usar terminología consistente (mínimo/moderado/significativo)\r\n\r\nMUY IMPORTANTE!!!!!\r\n*SOLO DEVOLVER EL JSON FINAL*\r\n"{\\r\\n  \\"company\\": {\\r\\n    \\"name\\": \\"[Se agregará automáticamente del sistema]\\",\\r\\n    \\"image_url\\": \\"[Se agregará automáticamente del sistema]\\",\\r\\n    \\"intro\\": \\"[Texto introductorio del programa institucional]\\"\\r\\n  },\\r\\n  \\"competencias\\": {\\r\\n    \\"altas\\": [\\r\\n      {\\r\\n        \\"nombre\\": \\"Nombre de competencia\\",\\r\\n        \\"puntaje\\": 90,\\r\\n        \\"definicion\\": \\"Definición exacta de la competencia\\",\\r\\n        \\"descripcion\\": \\"Descripción breve de 1 línea\\",\\r\\n        \\"analisisDetallado\\": \\"Análisis CONCISO de 2 líneas con evidencia clave\\",\\r\\n        \\"relevanciaOrganizacional\\": \\"1 línea sobre conexión con la organización\\"\\r\\n      }\\r\\n    ],\\r\\n    \\"medias\\": [\\r\\n      {\\r\\n        \\"nombre\\": \\"Nombre de competencia\\",\\r\\n        \\"puntaje\\": 75,\\r\\n        \\"definicion\\": \\"Definición exacta de la competencia\\",\\r\\n        \\"descripcion\\": \\"Descripción breve de 1 línea\\",\\r\\n        \\"analisisDetallado\\": \\"Análisis CONCISO de 2 líneas con evidencia clave\\",\\r\\n        \\"relevanciaOrganizacional\\": \\"1 línea sobre conexión con la organización\\"\\r\\n      }\\r\\n    ],\\r\\n    \\"bajas\\": [\\r\\n      {\\r\\n        \\"nombre\\": \\"Nombre de competencia\\",\\r\\n        \\"puntaje\\": 60,\\r\\n        \\"definicion\\": \\"Definición exacta de la competencia\\",\\r\\n        \\"descripcion\\": \\"Descripción breve de 1 línea\\",\\r\\n        \\"analisisDetallado\\": \\"Análisis CONCISO de 2 líneas con evidencia clave\\",\\r\\n        \\"relevanciaOrganizacional\\": \\"1 línea sobre conexión con la organización\\"\\r\\n      }\\r\\n    ]\\r\\n  },\\r\\n  \\"conclusiones\\": {\\r\\n    \\"resumenFinal\\": \\"Párrafo CONCISO de 4-5 líneas con insights clave\\",\\r\\n    \\"recomendacionPrincipal\\": \\"1 recomendación específica\\",\\r\\n    \\"areas\\": [\\r\\n      {\\r\\n        \\"nombre\\": \\"NOMBRE DE LA COMPETENCIA\\",\\r\\n        \\"objetivo\\": \\"X% en Y meses\\",\\r\\n        \\"descripcion\\": \\"1 línea sobre el área de desarrollo\\",\\r\\n        \\"accionInmediata\\": \\"1 acción concreta\\"\\r\\n      }\\r\\n    ]\\r\\n  },\\r\\n  \\"perfilGeneral\\": {\\r\\n    \\"resumenDescriptivo\\": \\"Párrafo de 80-100 palabras\\",\\r\\n    \\"metodologia\\": \\"METODOLOGIA: \\"Metodología Re-skilling.AI: Análisis Psicométrico Multimodal\\"\\r\\n\\"Evaluación basada en análisis que combina técnicas proyectivas tradicionales con tecnología de procesamiento de lenguaje natural. Un modelo de IA especializado (LLM), entrenado en marcos teóricos de evaluación psicológica y competencias organizacionales, analiza  respuestas de audio evaluando tanto contenido semántico como indicadores prosódicos (estabilidad emocional, confianza, energía vocal). Esta metodología multimodal permite identificar patrones comportamentales profundos y generar predicciones de empleabilidad con alta validez predictiva.\\",\\r\\n    \\"matchGlobal\\": \\"XX% - Interpretación breve\\"\\r\\n  },\\r\\n  \\"datosPersonales\\": {\\r\\n    \\"nombre\\": \\"[Se agregará automáticamente del sistema]\\",\\r\\n    \\"email\\": \\"[Se agregará automáticamente del sistema]\\",\\r\\n    \\"fechaTest\\": \\"[Fecha actual]\\",\\r\\n    \\"nombreUniversidad\\": \\"[Extraer de respuestas o No especificada]\\"\\r\\n  },\\r\\n  \\"datosGraficoRadar\\": {\\r\\n    \\"labels\\": [\\r\\n      \\"Perseverancia\\",\\r\\n      \\"Resiliencia\\",\\r\\n      \\"Pensamiento Crítico y Adaptabilidad\\",\\r\\n      \\"Regulación Emocional\\",\\r\\n      \\"Responsabilidad\\",\\r\\n      \\"Autoconocimiento\\",\\r\\n      \\"Manejo del Estrés\\",\\r\\n      \\"Asertividad\\",\\r\\n      \\"Habilidad para Construir Relaciones\\",\\r\\n      \\"Creatividad\\",\\r\\n      \\"Empatía\\",\\r\\n      \\"Capacidad de Influencia y Comunicación\\",\\r\\n      \\"Capacidad y Estilo de Liderazgo\\",\\r\\n      \\"Curiosidad y Capacidad de Aprendizaje\\",\\r\\n      \\"Tolerancia a la Frustración\\"\\r\\n    ],\\r\\n    \\"valores\\": {\\r\\n      \\"serie1\\": [\\"puntaje_evaluado_1\\", \\"puntaje_evaluado_2\\", \\"...\\", \\"puntaje_evaluado_15\\"],\\r\\n      \\"serie2\\": [\\"70\\", \\"80\\", \\"90\\", \\"70\\", \\"90\\", \\"70\\", \\"80\\", \\"80\\", \\"80\\", \\"70\\", \\"80\\", \\"90\\", \\"90\\", \\"80\\", \\"70\\"]\\r\\n    }\\r\\n  }\\r\\n}"	\N	claude-sonnet-4-20250514	0	t	2025-11-27 01:38:21.647721	2025-11-27 01:38:21.647723
\.


--
-- Data for Name: documents; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.documents (id, tenant_id, title, document_type, filename, source, chunks_count, status, error_message, created_at, updated_at) FROM stdin;
6f10dd83-be08-43f1-b46c-1a65c823b74e	14ada894-8da9-4073-b68a-fe0c1cd436b1	-Inteligencia-Emocional	methodology	-Inteligencia-Emocional.pdf	\N	35	completed	\N	2025-11-27 01:29:27.179549	2025-11-27 01:29:30.073693
1945635e-7289-4211-9bc5-ce0958e48001	14ada894-8da9-4073-b68a-fe0c1cd436b1	Assessment-Centers-in-Human-Resource-Management	methodology	Assessment-Centers-in-Human-Resource-Management.pdf	\N	0	processing	\N	2025-11-27 01:30:11.2767	2025-11-27 01:30:11.276701
f6541784-8c5b-4a5c-a49e-f9825c20153b	14ada894-8da9-4073-b68a-fe0c1cd436b1	The psychology of language comunication	methodology	-The-Psychology-of-Language-Communication-pdf.pdf	\N	244	completed	\N	2025-11-27 01:17:13.509485	2025-11-27 01:18:41.263709
189717ca-6cf7-4421-a0bd-fc4882b90cfa	14ada894-8da9-4073-b68a-fe0c1cd436b1	Emotion-Affect-and-Personality-in-Speech-The-Bias-of-Language-and-Paralan	methodology	491351852-Emotion-Affect-and-Personality-in-Speech-The-Bias-of-Language-and-Paralan.pdf	\N	210	completed	\N	2025-11-27 01:22:00.984427	2025-11-27 01:22:36.187083
3ee6aec4-c4ae-4647-b517-ca6304cecffb	14ada894-8da9-4073-b68a-fe0c1cd436b1	Emotion dimensions and formant position	methodology	852588272-Emotion-dimension-and-formant-position.pdf	\N	30	completed	\N	2025-11-27 01:24:11.918157	2025-11-27 01:24:16.930706
4d429605-d196-4273-a4f7-320d5b4ea54c	14ada894-8da9-4073-b68a-fe0c1cd436b1	CAREER CONSTRUCTION THEORY	methodology	Career_frases_incompletas.pdf	\N	35	completed	\N	2025-11-27 01:24:37.603477	2025-11-27 01:24:46.494044
89624b27-d6af-48e7-ba31-a88cb07156d6	14ada894-8da9-4073-b68a-fe0c1cd436b1	Decoding speech prosody in five languages	methodology	Decoding-Speech-Prosody-in-Five-Languages.pdf	\N	59	completed	\N	2025-11-27 01:25:18.850085	2025-11-27 01:25:26.13005
0f23fddc-27b9-4930-a8b2-ef051dead49e	14ada894-8da9-4073-b68a-fe0c1cd436b1	holaday2000	methodology	holaday2000.pdf	\N	58	completed	\N	2025-11-27 01:25:40.546238	2025-11-27 01:25:50.112254
171a2776-363d-44ee-b1e9-f4e693030929	14ada894-8da9-4073-b68a-fe0c1cd436b1	MANUAL-DEL-TEST-DE-ROTTER_-_frases_incompletas	methodology	MANUAL-DEL-TEST-DE-ROTTER_-_frases_incompletas.pdf	\N	34	completed	\N	2025-11-27 01:25:57.290501	2025-11-27 01:26:07.878727
e1fde39b-fda0-46ef-8143-b800a5eebfe3	14ada894-8da9-4073-b68a-fe0c1cd436b1	Mcadams_largo	methodology	Mcadams_largo.pdf	\N	158	completed	\N	2025-11-27 01:26:17.629124	2025-11-27 01:26:56.169004
150c7b60-a36f-4f2a-a902-bd897124c511	14ada894-8da9-4073-b68a-fe0c1cd436b1	McAdams-Narrative-Identity	methodology	McAdams-Narrative-Identity.pdf	\N	42	completed	\N	2025-11-27 01:27:02.95447	2025-11-27 01:27:16.831058
5bde98cd-cfeb-4f17-ad3c-cb61f37f7e44	14ada894-8da9-4073-b68a-fe0c1cd436b1	narrative-analysis	methodology	narrative-analysis.pdf	\N	39	completed	\N	2025-11-27 01:27:23.032973	2025-11-27 01:27:27.447214
6abd7dfc-666b-4c35-842b-52a612613ec1	14ada894-8da9-4073-b68a-fe0c1cd436b1	Prosodia_	methodology	Prosodia_.pdf	\N	30	completed	\N	2025-11-27 01:27:40.732751	2025-11-27 01:27:48.417776
7ff724f1-811d-434f-a71c-b46d8196ab8a	14ada894-8da9-4073-b68a-fe0c1cd436b1	Prosodia_2	methodology	PROSODIA-A-veces-la-voz-dice-mas-que-las-palabras.pdf	\N	74	completed	\N	2025-11-27 01:28:07.982724	2025-11-27 01:28:21.463171
de51a25c-f64f-420a-865e-23fce88e9a72	14ada894-8da9-4073-b68a-fe0c1cd436b1	-Critical-Behavior-Inteviewing-Strategies-for-Candidates-Recruiters-1	methodology	-Critical-Behavior-Inteviewing-Strategies-for-Candidates-Recruiters-1.pdf	\N	17	completed	\N	2025-11-27 01:28:44.522138	2025-11-27 01:28:51.344067
717cf8df-15c3-4562-aeb6-ef0d4c6b8235	14ada894-8da9-4073-b68a-fe0c1cd436b1	-Inteligencia-emocional-por-Mayer-y-Salovey	methodology	-Inteligencia-emocional-por-Mayer-y-Salovey.pdf	\N	90	completed	\N	2025-11-27 01:29:01.532303	2025-11-27 01:29:19.748714
64da3825-8b50-479a-a84b-a840d2dce9b4	14ada894-8da9-4073-b68a-fe0c1cd436b1	Daniel-Goleman	methodology	Daniel-Goleman.pdf	\N	18	completed	\N	2025-11-27 01:33:10.200722	2025-11-27 01:33:19.976557
e8a7f1cf-23e1-47f1-9b6d-f88c65432852	14ada894-8da9-4073-b68a-fe0c1cd436b1	Discusion_Emotional-Intelligence-by-Goleman	methodology	Discusion_Emotional-Intelligence-by-Goleman.pdf	\N	30	completed	\N	2025-11-27 01:33:51.321383	2025-11-27 01:33:54.810285
3c1373c6-bad9-4202-ab74-c48d671ba659	14ada894-8da9-4073-b68a-fe0c1cd436b1	Gofe-Bei-Instructions-2016-Nov	methodology	Gofe-Bei-Instructions-2016-Nov.pdf	\N	21	completed	\N	2025-11-27 01:34:15.987361	2025-11-27 01:34:17.78737
0c9a27a3-bf10-4f12-b382-d033b250fb83	14ada894-8da9-4073-b68a-fe0c1cd436b1	Grounded-Theory	methodology	Grounded-Theory.pdf	\N	29	completed	\N	2025-11-27 01:34:33.495314	2025-11-27 01:34:37.285586
\.


--
-- Data for Name: tenant_prompts; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.tenant_prompts (id, tenant_id, prompt_type, name, content, is_active, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: tenants; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.tenants (id, name, slug, description, is_active, created_at, updated_at) FROM stdin;
14ada894-8da9-4073-b68a-fe0c1cd436b1	Reskilling	reskilling	\N	t	2025-11-27 00:57:45.113314	2025-11-27 00:57:45.113319
\.


--
-- Name: api_keys api_keys_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.api_keys
    ADD CONSTRAINT api_keys_pkey PRIMARY KEY (id);


--
-- Name: assistants assistants_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.assistants
    ADD CONSTRAINT assistants_pkey PRIMARY KEY (id);


--
-- Name: documents documents_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_pkey PRIMARY KEY (id);


--
-- Name: tenant_prompts tenant_prompts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tenant_prompts
    ADD CONSTRAINT tenant_prompts_pkey PRIMARY KEY (id);


--
-- Name: tenants tenants_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tenants
    ADD CONSTRAINT tenants_pkey PRIMARY KEY (id);


--
-- Name: ix_api_keys_key_prefix; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_api_keys_key_prefix ON public.api_keys USING btree (key_prefix);


--
-- Name: ix_api_keys_tenant_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_api_keys_tenant_id ON public.api_keys USING btree (tenant_id);


--
-- Name: ix_assistants_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_assistants_name ON public.assistants USING btree (name);


--
-- Name: ix_assistants_slug; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_assistants_slug ON public.assistants USING btree (slug);


--
-- Name: ix_assistants_tenant_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_assistants_tenant_id ON public.assistants USING btree (tenant_id);


--
-- Name: ix_documents_tenant_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_documents_tenant_id ON public.documents USING btree (tenant_id);


--
-- Name: ix_tenant_prompts_prompt_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tenant_prompts_prompt_type ON public.tenant_prompts USING btree (prompt_type);


--
-- Name: ix_tenant_prompts_tenant_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tenant_prompts_tenant_id ON public.tenant_prompts USING btree (tenant_id);


--
-- Name: ix_tenants_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tenants_name ON public.tenants USING btree (name);


--
-- Name: ix_tenants_slug; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_tenants_slug ON public.tenants USING btree (slug);


--
-- Name: api_keys api_keys_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.api_keys
    ADD CONSTRAINT api_keys_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: assistants assistants_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.assistants
    ADD CONSTRAINT assistants_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: documents documents_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: tenant_prompts tenant_prompts_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tenant_prompts
    ADD CONSTRAINT tenant_prompts_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- PostgreSQL database dump complete
--

\unrestrict 3leU2NQaJH2TfLPRejScF4DMr8QoN6swIDVuq1TA42zVk94zTyV78k9uWvqZTlC

