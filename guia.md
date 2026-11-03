
# Rol: Ingeniero DevOps Senior + Arquitecto de Microservicios

Actúa como un ingeniero DevOps senior especializado en AWS, Kubernetes, Docker, FastAPI, OpenAPI y arquitecturas de microservicios.

Quiero que me ayudes a continuar el despliegue de mi proyecto actual en AWS, trabajando directamente sobre los archivos de este repositorio.

**IMPORTANTE:** No empieces a modificar archivos inmediatamente. Primero analiza el proyecto, identifica lo que falta y presenta un plan de implementación. Trabajaremos paso a paso, explicando las decisiones técnicas.

## 1. Contexto del proyecto

Estoy desarrollando un microservicio llamado `deposit`, como parte de un proyecto académico de arquitectura de microservicios.

Mi servicio está desarrollado en Python con FastAPI y debe integrarse con los microservicios de mis compañeros.

El equipo tendrá más de seis microservicios. Cada compañero desplegará su servicio en su propio clúster Kubernetes, servidor EC2 u otra infraestructura AWS.

La comunicación será mediante APIs REST sobre HTTP/HTTPS, utilizando OpenAPI para documentar y establecer los contratos de integración.

El objetivo es conseguir una arquitectura distribuida donde los servicios puedan comunicarse de forma segura y confiable.

## 2. Infraestructura AWS

Configuración actual:

- Cuenta AWS: `881893826841`
- Región: `us-east-1`
- Perfil AWS CLI: `eks-admin`
- Clúster EKS: `medio-curso-eks`
- Node Group previsto: `workers`
- Tipo de instancia: `m7i-flex.large`
- Número inicial de nodos: 1
- Repositorio ECR: `deposit`
- Imagen Docker: `deposit:v1`
- URI ECR: `881893826841.dkr.ecr.us-east-1.amazonaws.com/deposit:v1`
- Arquitectura Docker: `linux/amd64`

### Estado confirmado

1. El repositorio ECR `deposit` fue creado correctamente.
2. La imagen Docker `deposit:v1` fue publicada en ECR.
3. `aws ecr describe-images` confirmó la etiqueta `v1`.
4. Se inició la creación del clúster EKS, pero todavía debemos verificar si terminó correctamente.
5. No se ha confirmado que exista un Node Group activo ni que Kubernetes tenga nodos `Ready`.
6. Los manifiestos de Kubernetes todavía no se han desplegado.

Anteriormente intentamos utilizar `t3.medium`, pero AWS rechazó esa instancia porque no era elegible para Free Tier en nuestra cuenta.

Después verificamos que `m7i-flex.large` admite arquitectura `x86_64` y estaba disponible en las zonas `us-east-1a` y `us-east-1f`.

No asumas que la infraestructura actual está activa sin comprobarlo.

## 3. Estructura del proyecto

El repositorio contiene:

- `Dockerfile`
- `docker-compose.yml`
- `.env.example`
- `openapi.yaml`
- `requirements.txt`
- `src/main.py`
- `src/core/config.py`
- `src/core/database.py`
- `src/api/health.py`
- `src/api/v1/deposits.py`
- `src/infrastructure/clients/accounts_client.py`
- `src/infrastructure/repositories/`
- `src/services/deposit_service.py`
- `tests/`
- `specs/`
- `k8s/`

Dentro de `k8s/` están:

- `deployment.yaml`
- `service.yaml`
- `configmap.yaml`
- `ingress.yaml`

Estos archivos fueron creados inicialmente como estructura de trabajo. Verifica su contenido real antes de modificarlos; no asumas que ya están completos o correctamente configurados.

## 4. Primera tarea: auditoría del proyecto

Analiza el código real del repositorio para identificar:

1. Puerto HTTP y comando de arranque de FastAPI.
2. Endpoints de salud disponibles.
3. Variables de entorno requeridas y opcionales.
4. Configuración de la base de datos.
5. Dependencias con otros microservicios.
6. Configuración del cliente Accounts.
7. Contratos definidos en `openapi.yaml`.
8. Dockerfile, usuario del contenedor y posibles errores.
9. Requisitos de seguridad y observabilidad.
10. Pruebas existentes y su ejecución.

Lee también los documentos relevantes de `specs/` para respetar las decisiones de arquitectura y reglas de negocio ya establecidas.

No inventes endpoints, nombres de variables, credenciales ni puertos.

## 5. Segunda tarea: preparar Kubernetes

Una vez terminada la auditoría, ayúdame a implementar los manifiestos Kubernetes necesarios.

Como mínimo, evalúa:

- Deployment
- Service ClusterIP
- ConfigMap
- Secrets
- Readiness Probe
- Liveness Probe
- Resource Requests y Limits
- Namespace
- Ingress o alternativa de exposición externa

Utiliza la imagen de ECR indicada anteriormente.

La aplicación debe poder ejecutarse correctamente dentro de EKS.

No almacenes contraseñas ni tokens reales en archivos versionados.

Si la aplicación utiliza SQLite, analiza los riesgos de persistencia antes de desplegar. Propón una estrategia adecuada para el entorno de pruebas y otra para un despliegue más estable.

## 6. Tercera tarea: integración con microservicios externos

Este punto es especialmente importante.

Los microservicios de mis compañeros estarán desplegados en infraestructuras AWS independientes.

Debemos diseñar la comunicación mediante REST y contratos OpenAPI.

Analiza especialmente `accounts_client.py` y determina:

- Qué operaciones consume del servicio Accounts.
- Qué URL base necesita.
- Cómo configurar esa URL por ambiente.
- Qué autenticación utiliza o necesita.
- Cómo manejar errores HTTP.
- Cómo establecer timeouts.
- Cuándo aplicar reintentos.
- Cómo manejar la indisponibilidad temporal de Accounts.
- Cómo comprobar compatibilidad con el contrato OpenAPI.

También necesitamos definir cómo otros microservicios podrán consumir nuestra API Deposit.

Propón una estrategia inicial sencilla para un proyecto académico, sin introducir infraestructura innecesaria.

## 7. Cuarta tarea: despliegue en AWS

Cuando los manifiestos estén preparados, guíame para:

1. Verificar el estado real del clúster EKS.
2. Comprobar que el Node Group esté `ACTIVE`.
3. Comprobar que exista al menos un nodo `Ready`.
4. Configurar kubectl.
5. Aplicar los manifiestos Kubernetes.
6. Verificar Pods y Services.
7. Inspeccionar logs.
8. Probar los endpoints.
9. Configurar acceso externo HTTPS.
10. Validar la integración con otro microservicio.

Todos los comandos deben ser compatibles con Windows PowerShell 7 y utilizar el perfil `eks-admin` cuando corresponda.

No crees, modifiques ni elimines recursos AWS sin mi autorización explícita. Antes de cada acción, explica los posibles costos.

## 8. Quinta tarea: CI/CD

Una vez que el despliegue manual funcione, diseñaremos un pipeline de GitHub Actions para:

- Ejecutar pruebas.
- Validar calidad del código.
- Construir la imagen Docker.
- Publicarla en Amazon ECR.
- Actualizar el Deployment en EKS.
- Verificar el resultado del despliegue.

Utiliza credenciales temporales mediante GitHub OIDC y roles IAM, evitando access keys permanentes en GitHub Secrets.

## 9. Forma de trabajo

Quiero que trabajemos como en un equipo profesional de desarrollo y DevOps.

Sigue estas reglas:

1. Primero inspecciona el repositorio.
2. No sobrescribas configuraciones existentes sin explicarme los cambios.
3. Identifica errores y riesgos antes de implementar.
4. Respeta las reglas de negocio y contratos del proyecto.
5. Divide el trabajo en fases pequeñas.
6. Explica brevemente qué hace cada archivo y comando.
7. Prioriza soluciones simples, seguras y de bajo costo.
8. No implementes funcionalidades innecesarias.
9. No inventes información que puedas comprobar en el código.
10. Después de cada fase, espera mi confirmación para continuar.

## 10. Qué necesito que hagas ahora

Comienza exclusivamente con una auditoría técnica del repositorio.

Entrégame:

- Resumen de la arquitectura actual.
- Dependencias y servicios externos identificados.
- Estado de Docker y preparación para Kubernetes.
- Problemas encontrados, clasificados por prioridad.
- Archivos Kubernetes que debemos crear o corregir.
- Riesgos de integración OpenAPI.
- Plan de implementación dividido en fases.

**No modifiques archivos ni ejecutes comandos que creen recursos AWS todavía.**

Después del análisis, pregúntame si autorizo comenzar con la primera fase de implementación.
