# Auditoría Técnica y Diagnóstico de Arquitectura

**Proyecto**: Microservicio Bancario de Depósitos en Dólares (`deposit`)  
**Fecha de Auditoría**: Noviembre 2026  
**Entorno de Nube**: AWS EKS (`medio-curso-eks`), Región `us-east-1`  
**Cuenta AWS**: `881893826841`  

---

## 1. Resumen de la Arquitectura Actual

El microservicio **`deposit`** (USD Deposit Microservice) está implementado en Python y sigue los principios de Clean Architecture / Puertos y Adaptadores:

- **Framework Web**: FastAPI (v0.110+) con servidor ASGI Uvicorn.
- **Estructura por Capas**:
  - `src/api/`: Controladores REST (`v1/deposits.py`), endpoints de salud (`health.py`) e inyección de dependencias (`dependencies.py`).
  - `src/domain/`: Modelos de dominio (`models.py`), tipos de canales (`ChannelType`), estados de transacción (`DepositStatus`) y reglas de negocio puras (`rules.py`).
  - `src/services/`: Orquestación de la lógica financiera (`deposit_service.py`), verificación de idempotencia y validación contra lavado de dinero (AML).
  - `src/infrastructure/`: Modelos ORM de SQLAlchemy (`db_models.py`), repositorios asíncronos (`deposit_repository.py`, `idempotency_repository.py`) y cliente HTTP externo (`accounts_client.py`).
  - `src/core/`: Configuración centralizada vía Pydantic Settings (`config.py`), base de datos (`database.py`), excepciones tipadas (`exceptions.py`) y logging contextual estructurado (`logging.py`).
- **Manejo de Errores Financieros**: Estandarizado bajo **RFC 7807 / RFC 9457 (Problem Details)** devolviendo el content-type `application/problem+json`.
- **Trazabilidad y Observabilidad**: Middleware HTTP asíncrono que genera o propaga la cabecera `X-Correlation-ID` en cada solicitud y respuesta, registrando logs estructurados con tiempo de respuesta en milisegundos (`duration_ms`).

---

## 2. Dependencias y Servicios Externos Identificados

| Dependencia / Servicio | Tipo | Protocolo / Contrato | Función en el Flujo |
| :--- | :--- | :--- | :--- |
| **Microservicio de Cuentas (`accounts-service`)** | Externa (compañero) | REST HTTP/JSON (`/api/v1/accounts/*`) | 1. Consulta elegibilidad y moneda (`GET /api/v1/accounts/{id}`).<br>2. Acredita saldo (`POST /api/v1/accounts/{id}/credits`). |
| **Base de Datos Relacional** | Interna | SQL asíncrono (SQLAlchemy + `aiosqlite` o `asyncpg`) | Persistencia de transacciones de depósito, auditoría e historial de idempotencia. |
| **Clientes Consumidores** | Entrantes (otros microservicios / canales) | REST HTTP/JSON sobre `/api/v1/deposits/usd` | Microservicios de Retiros, Billeteras, Sucursales físicas (`BRANCH`) y Cajeros (`ATM`). |

---

## 3. Estado de Docker y Preparación para Kubernetes

### Dockerfile
- **Multi-stage build**:
  - Etapa 1 (`builder`): `python:3.11-slim`, instala herramientas de compilación y dependencias con `pip install --user`.
  - Etapa 2 (`runner`): `python:3.11-slim`, crea usuario no root `appuser` (UID 1000) por seguridad bancaria.
- **Imagen en ECR confirmada**:
  - Repositorio: `881893826841.dkr.ecr.us-east-1.amazonaws.com/deposit`
  - Etiqueta: `v1`
  - Digest verificado: `sha256:7dce1defb5717d1bf5efa04681b41404d1f41894bd0e837569b8a032406be752`
  - Tamaño: ~74.95 MB

### Estado Real de la Infraestructura en AWS (Verificado en Vivo)
- **Clúster EKS**: `medio-curso-eks` (v1.34) se encuentra en estado **`ACTIVE`**.
- **Node Group**: `workers` con tipo de instancia `m7i-flex.large` se encuentra en estado **`ACTIVE`**.
- **Nodos EKS**: 1 nodo EC2 `ip-192-168-31-52.ec2.internal` en estado **`Ready`**.
- **Conectividad kubectl**: Conexión establecida mediante perfil `eks-admin`. Componentes de sistema (`coredns`, `kube-proxy`, `aws-node`, `metrics-server`) en ejecución normal.
- **Despliegue de aplicación**: Aún no se han aplicado los manifiestos de Kubernetes en el clúster.

---

## 4. Problemas Encontrados (Clasificados por Prioridad)

### 🔴 Prioridad Alta (Bloqueantes para Producción o Kubernetes)

1. **`k8s/deployment.yaml` desconectado de variables de entorno**:
   - El Deployment carece de bloque `env` o `envFrom`. El contenedor en el pod arrancará con las variables predeterminadas del archivo `.env.example` copiado en la imagen, intentando conectar a `http://localhost:8081` para el servicio de Cuentas, fallando cualquier transacción.
2. **Discrepancia en variables en `k8s/configmap.yaml`**:
   - Define `APP_ENV: "production"`, pero `src/core/config.py` lee la variable `ENV` (no `APP_ENV`). Además, no contiene las variables de conexión a red (`ACCOUNTS_SERVICE_URL`, `PORT`, `DATABASE_URL`).
3. **Probes de Kubernetes mal asignados en `deployment.yaml`**:
   - Tanto `readinessProbe` como `livenessProbe` apuntan a `/health/live`.
   - `readinessProbe` debe apuntar a `/health/ready` para asegurar que el pod no reciba tráfico antes de que la base de datos esté lista.
4. **Contradicción arquitectónica en `src/api/health.py` vs SPEC-04**:
   - `readiness` marca `NOT_READY` (HTTP 503) si el Circuit Breaker de Cuentas está `OPEN`.
   - **SPEC-04 (RES-003, L33)** indica explícitamente: *"Cuentas caída no retira la API de readiness: el servicio puede aceptar duraderamente y consultar recursos"*. Retirar el pod de los endpoints ante fallas de un servicio downstream genera un fallo en cascada en Kubernetes.
5. **Riesgo de persistencia de SQLite en Kubernetes**:
   - Si se usa SQLite (`./deposits.db`), el archivo reside dentro del sistema de archivos efímero del contenedor. Al reiniciarse el Pod o desplegar una nueva versión, se pierden todas las transacciones. Además, impide escalar horizontalmente a más de 1 réplica.
6. **`k8s/ingress.yaml` vacío (0 bytes)**:
   - No hay configuración de entrada ni balanceo externo para exponer el servicio a los microservicios de los compañeros fuera del clúster.

### 🟡 Prioridad Media (Calidad, Observabilidad y Docker)

7. **Falta de `curl` en la etapa `runner` del Dockerfile**:
   - El `HEALTHCHECK` del Dockerfile invoca `curl -f http://localhost:8000/health/live`. Sin embargo, `curl` solo fue instalado en la etapa `builder`, no en `runner`. En Docker nativo el contenedor pasa a estado `unhealthy` por comando no encontrado.
8. **Ausencia de autenticación / autorización en endpoints de negocio**:
   - A diferencia de los lineamientos de integración inter-servicios (donde se exige `Authorization: Bearer <JWT>`), los endpoints de FastAPI en `deposits.py` no exigen ni validan tokens JWT.
9. **Falta de configuración de PYTHONPATH para pruebas locales**:
   - Al ejecutar `pytest` se genera error por ausencia de `pythonpath = .` en `pytest.ini` y falta de dependencias de test en el entorno global.

### 🟢 Prioridad Baja (Mantenibilidad)

10. **Hardcode de puerto en `Dockerfile`**:
    - El CMD fija `--port 8000`, ignorando si la variable `PORT` del entorno cambia a otro valor.

---

## 5. Archivos Kubernetes a Crear o Corregir

| Archivo | Acción | Descripción |
| :--- | :--- | :--- |
| `k8s/namespace.yaml` | **Crear** | Aislar los recursos en el namespace dedicado `deposit`. |
| `k8s/configmap.yaml` | **Corregir** | Mapear `ENV`, `PORT`, `LOG_LEVEL`, `ACCOUNTS_SERVICE_URL` y límites financieros. |
| `k8s/secret.example.yaml` | **Crear** | Plantilla de secrets para credenciales sensibles sin comprometer seguridad en git. |
| `k8s/deployment.yaml` | **Corregir** | Enlazar `configMapRef`, corregir rutas de probes (`/health/ready` y `/health/live`), `securityContext` bancario y límites de recursos. |
| `k8s/service.yaml` | **Ajustar** | Configurar Service tipo `ClusterIP` con namespace `deposit` y mapeo de puertos 80:8000. |
| `k8s/kustomization.yaml` | **Crear** | Orquestar el despliegue ordenado de todos los recursos con `kubectl apply -k k8s/`. |
| `k8s/ingress.yaml` | **Implementar** | Configurar exposición externa (AWS Load Balancer / Ingress). |

---

## 6. Riesgos de Integración OpenAPI y Microservicios

1. **Conectividad Inter-Clúster / Inter-VPC**:
   - Cada compañero tiene infraestructura independiente en AWS. Se requiere una URL accesible por internet (NLB/ALB con IP pública o DNS) parametrizable en `ACCOUNTS_SERVICE_URL`.
2. **Formato Monetario**:
   - `deposit` opera con strings con dos decimales (`"1500.50"`) bajo `Decimal`. Otros microservicios (como retiros) pueden usar enteros en céntimos (`1500`). Se debe vigilar el contrato de datos.
3. **Idempotencia en Cuentas**:
   - Ante reintentos o timeouts, el microservicio de Cuentas debe deduplicar por `deposit_reference` para evitar acreditaciones dobles de fondos.

---

## 7. Plan de Implementación por Fases

- **Fase 1**: Preparación y corrección integral de manifiestos Kubernetes (`k8s/`).
- **Fase 2**: Despliegue manual en AWS EKS y verificación de pods y logs.
- **Fase 3**: Estrategia de persistencia de base de datos y ajuste de resiliencia.
- **Fase 4**: Exposición externa e integración con microservicios de compañeros.
- **Fase 5**: Pipeline CI/CD con GitHub Actions y autenticación AWS OIDC.

