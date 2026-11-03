# Próximos Pasos y Guía de Operación — Microservicio `deposit`

Este documento resume las tareas pendientes para la siguiente sesión de trabajo, las opciones de integración con el equipo y los comandos rápidos para reactivar o pausar la infraestructura en AWS minimizando costos.

---

## 1. Estado Actual del Microservicio

- **Código y Contratos**: Microservicio en FastAPI probado y validado con RFC 7807/9457 y reglas AML.
- **Contrato de Integración**: Documentado en [CONTRATO-INTEGRACION-DEPOSITOS.md](file:///c:/Users/ThikPad/Desktop/MESE%20VIII/DESARROLLO%20DE%20APLICACIONES%20PARA%20LA%20NUBE/microservicios/microservicio/CONTRATO-INTEGRACION-DEPOSITOS.md).
- **Pipeline CI/CD**: Implementado en GitHub Actions con autenticación AWS OIDC (sin credenciales estáticas). Cada `git push origin main` ejecuta pruebas automáticas, compila la imagen en Amazon ECR y actualiza Amazon EKS.
- **Mock de Cuentas**: Desplegado internamente en el clúster con Service `ClusterIP` para pruebas de extremo a extremo.

---

## 2. Tareas para la Siguiente Sesión

### Opción 1: Abrir el Acceso Público para la Integración con Compañeros
Cuando los equipos de **Retiros**, **Billeteras** u otros canales vayan a invocar tu microservicio:

1. **Reactivar el balanceador de carga público**:
   En `k8s/service.yaml`, verificar que el tipo sea `LoadBalancer`:
   ```yaml
   spec:
     type: LoadBalancer
     # Para permitir a cualquier compañero:
     # retira 'loadBalancerSourceRanges' o añade sus IPs públicas:
     loadBalancerSourceRanges:
       - 190.43.149.147/32 # Tu IP
       - <IP_COMPAÑERO_1>/32
   ```
2. **Aplicar los cambios**:
   ```powershell
   kubectl apply -f k8s/service.yaml
   ```
3. **Compartir el DNS público**:
   Tus compañeros consumirán los endpoints en:
   `http://<DNS_DEL_LOAD_BALANCER>/api/v1/deposits/usd`

---

### Opción 2: Conectar con el Microservicio de Cuentas Real del Compañero
Cuando el compañero responsable del servicio de Cuentas tenga su servicio desplegado en AWS:

1. Solicitarle su URL base (ej: `http://54.x.x.x:8081` o su nombre DNS).
2. Modificar en [k8s/configmap.yaml](file:///c:/Users/ThikPad/Desktop/MESE%20VIII/DESARROLLO%20DE%20APLICACIONES%20PARA%20LA%20NUBE/microservicios/microservicio/k8s/configmap.yaml):
   ```yaml
   ACCOUNTS_SERVICE_URL: "http://<IP_O_DNS_DEL_COMPAÑERO>:8081"
   ```
3. Subir el cambio a GitHub:
   ```powershell
   git add k8s/configmap.yaml
   git commit -m "chore: apuntar a microservicio de cuentas real del companero"
   git push origin main
   ```
   *(El pipeline de GitHub Actions se encargará del despliegue automático).*

---

## 3. Guía Rápida para Pausar y Reactivar la Infraestructura (Control de Costos)

### Cómo Pausar Recursos (Lo ejecutado hoy para evitar costos)

1. **Eliminar el Balanceador de Carga (Ahorro: ~$0.54 USD/día)**:
   Convertir el servicio a `ClusterIP`:
   ```powershell
   kubectl patch svc deposit -n deposit -p '{"spec": {"type": "ClusterIP"}}'
   ```
   *(AWS destruye automáticamente el Load Balancer ELB).*

2. **Apagar la Instancia EC2 Worker (Ahorro: ~$2.35 USD/día)**:
   Escalar el grupo de nodos a 0 instancias:
   ```powershell
   aws eks update-nodegroup-config --cluster-name medio-curso-eks --nodegroup-name workers --scaling-config minSize=0,maxSize=1,desiredSize=0 --profile eks-admin --region us-east-1
   ```
   *(AWS termina la instancia `m7i-flex.large`, reduciendo el costo de cómputo a cero).*

---

### Cómo Reactivar los Recursos (El día que continúes)

1. **Encender la Instancia EC2 Worker**:
   ```powershell
   aws eks update-nodegroup-config --cluster-name medio-curso-eks --nodegroup-name workers --scaling-config minSize=1,maxSize=1,desiredSize=1 --profile eks-admin --region us-east-1
   ```
   *(En ~2 minutos el nodo estará en estado `Ready` y Kubernetes reanudará automáticamente los Pods de `deposit` y `accounts-mock`).*

2. **Reactivar el Balanceador de Carga Público**:
   ```powershell
   kubectl apply -f k8s/service.yaml
   ```
   *(En ~1 minuto AWS asignará el DNS público para recibir tráfico).*
