# Servicios evaluados como referente para SynapxIA

Antes de definir el alcance funcional de **SynapxIA**, se evaluaron las familias de
servicios y plataformas que hoy resuelven, de forma parcial y dispersa, el ciclo de vida de
los activos de software relacionados con **IA Generativa** (prompts, MCPs, agentes, flujos,
skills, asistentes, RAG y modelos). El objetivo del análisis no fue replicar ninguna de
ellas, sino **identificar las capacidades que debían converger en un único punto de
gobierno** y mapearlas a los módulos e historias de usuario (`HU-`) que SynapxIA finalmente
implementa.

La conclusión transversal: ninguna familia, por sí sola, gobierna el activo de IAGen
**de extremo a extremo** (taxonomía → propuesta → revisión → publicación → reutilización →
medición → conexión con procesos). SynapxIA toma de cada una la capacidad pertinente y la
articula sobre un modelo común (`assets` + `actions` + `characterizations` + taxonomía).

---

## Familias evaluadas y su adopción en SynapxIA

| Familia de servicio | Ejemplos de referencia | Capacidades evaluadas | Cómo lo capitaliza SynapxIA (módulo · HU) |
| --- | --- | --- | --- |
| **Repositorios DevOps / software forges** | GitHub, GitLab, Azure DevOps | Versionamiento, *pull requests* y revisión, *issues*, discusiones, *releases*, trazabilidad y relación con el código fuente. GitHub Discussions cubre preguntas/respuestas y anuncios; GitHub Releases empaqueta software con notas; Azure DevOps integra código, seguimiento de trabajo y CI/CD. ([GitHub Docs][1]) | **Workflow de contribución/revisión del activo** sobre `actions` (`PROPOSAL → REVIEW → PUBLICATION/REJECTION/MODIFICATION`), **versionamiento y deprecación** e **historial**. → **AI Library** · HU-LI02 (Propose), HU-LI09 (Versioning), HU-LI10 (History), HU-LI12–LI14 (Review/Show/Modify) |
| **Gestores de artefactos** | JFrog Artifactory, Sonatype Nexus | Registro formal y versionado de paquetes, binarios, contenedores, librerías y **modelos ML**. Artifactory es un repositorio universal (Maven, npm, PyPI, Docker, Helm, modelos ML); Nexus soporta múltiples formatos. ([JFrog][2]) | **Repositorio único de activos de IAGen** clasificado por taxonomía, como sustituto especializado del "artefacto" para activos de IA en lugar de binarios. → **AI Library** · HU-LI01 (Asset Repository) + **Asset Taxonomy** (categorías y *features*) |
| **Portales internos de desarrollo (IDP)** | Backstage, Port, Datadog IDP | Catálogo de servicios, *ownership*, documentación técnica, *scorecards*, acciones *self-service* y madurez operacional. Backstage modela entidades (componentes, APIs, recursos); Port añade catálogo, *scorecards* y acciones. ([Backstage][3]) | **Catálogo gobernado con *ownership* y permisos por audiencia**, **medición de adopción/madurez** por equipos y unidades, y **conexión con procesos** como contexto operativo. → **Collaboration** (equipos, dimensiones, métricas), **AI Library** · HU-LI08 (Permission), **Processes** |
| **Hubs de IA / ML / GenAI** | Hugging Face Hub, LangSmith, GPTs (ChatGPT) | Registro de modelos, *datasets*, apps de IA, **prompts**, versiones, metadatos, evaluaciones, permisos y publicación. Hugging Face aloja modelos/*datasets*/Spaces; LangSmith gestiona versiones de prompts y control de acceso; los GPTs se comparten en privado, por enlace o se publican. ([Hugging Face][4]) | **Catálogos curados por familia de activo** (galerías de prompts, MCPs, agentes, flujos, skills, asistentes, RAG, modelos) con **caracterizaciones** (metadatos por *feature*), permisos y publicación. → **AI Library** · HU-LI15–LI22 (catálogos) + HU-LI03 (Details/caracterización) |
| **Comunidades y Q&A interno** | Stack Internal, Discourse, GitHub Discussions | Foros, preguntas, **respuestas aceptadas**, comentarios, etiquetas, votación, reputación y conocimiento reutilizable. Stack Internal se posiciona como motor de conocimiento interno con gobernanza; Discourse crea conocimiento mediante conversación. ([Stack Overflow Business][5]) | **Capa comunitaria del activo**: votos, comentarios, preguntas/respuestas (hilos vía `parent`), favoritos y *tags*, todo sobre `actions` junto al activo. → **AI Library** · HU-LI04 (Favorite), HU-LI05 (Vote), HU-LI06 (Discussion) |
| **Gestión y priorización de iniciativas** | Aha!, Productboard, Jira Product Discovery | Captura de ideas/oportunidades, evaluación por criterios, priorización, diagnóstico y seguimiento del ciclo de vida. ([Aha!][6]) | **Módulo de iniciativas de IA** con activación, diagnóstico por criterios (claridad, soporte, complejidad, datos, riesgo, sostenibilidad), priorización e impacto esperado, sobre un workflow espejo en `collaborations`. → **Initiatives** · HU-IN03/04/12–14 |
| **BI / Analítica y *dashboards*** | Power BI, Looker Studio, Tableau, Metabase, Superset | Visualización de indicadores, *scorecards*, reportes embebidos, parámetros y control de acceso a tableros. ([Microsoft Learn][7]) | **Módulo de analítica** que registra y embebe tableros/reportes (página interna, Power BI, Looker, Tableau, Qlik, Metabase, Superset, *iframe*) con parámetros, ejecuciones, favoritos y permisos para observar **uso, adopción e impacto**. → **Analytics** · HU-AN |
| **Modelado de procesos / cadena de valor** | Herramientas BPMN, mapas de proceso, cadena de valor de Porter | Representación de procesos primarios y de soporte, mapas y modelos para ubicar dónde interviene la tecnología en la operación. | **Módulo de procesos** que modela cadenas de valor (procesos primarios/soporte de Porter), mapas y modelos para **conectar iniciativas y activos de IA con los procesos reales** del negocio. → **Processes** · HU-PR |

---

## Síntesis

SynapxIA no es "otro repositorio" ni "otro foro": es la **convergencia gobernada** de estas
ocho familias sobre un modelo de datos único, donde un mismo activo de IAGen se taxonomiza,
se propone y revisa con un *workflow* explícito, se caracteriza con metadatos, se discute y
se vota, se versiona y se reutiliza, se mide en su adopción y se conecta con los procesos del
negocio. Esa decisión de **articular en lugar de replicar** es la que da origen al alcance
funcional descrito en el [`README.md`](README.md).

---

[1]: https://docs.github.com/discussions?utm_source=chatgpt.com "GitHub Discussions documentation"
[2]: https://jfrog.com/artifactory/?utm_source=chatgpt.com "Artifactory | Universal Artifact Repository Manager"
[3]: https://backstage.io/docs/features/software-catalog/descriptor-format/?utm_source=chatgpt.com "Descriptor Format of Catalog Entities - Backstage"
[4]: https://huggingface.co/docs/hub/en/index?utm_source=chatgpt.com "Hugging Face Hub documentation"
[5]: https://stackoverflow.co/internal/?utm_source=chatgpt.com "Stack Internal – knowledge engine (formerly ...)"
[6]: https://www.aha.io/ "Aha! — Product development software"
[7]: https://learn.microsoft.com/power-bi/ "Power BI documentation - Microsoft Learn"
