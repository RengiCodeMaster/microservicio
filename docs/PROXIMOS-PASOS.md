# Próximos Pasos y Guía de Operación — Microservicio `deposit`

Este documento contiene la información completa para reanudar el proyecto en tu próxima sesión de trabajo, las opciones de integración con tus compañeros y las instrucciones para volver a crear el clúster con **cero costo durante el tiempo de inactividad**.

---

## 1. Estado Actual del Proyecto

- **Código y Contratos**: Microservicio en Python/FastAPI con RFC 7807/9457 y reglas AML.
- **Contrato de Integración**: Documentado en [CONTRATO-INTEGRACION-DEPOSITOS.md](file:///c:/Users/ThikPad/Desktop/MESE%20VIII/DESARROLLO%20DE%20APLICACIONES%20PARA%20LA%20NUBE/microservicios/microservicio/CONTRATO-INTEGRACION-DEPOSITOS.md).
- **Pipeline CI/CD**: Implementado en GitHub Actions con autenticación AWS OIDC (sin credenciales estáticas). Cada `git push origin main` ejecuta pruebas automáticas, compila la imagen en Amazon ECR y actualiza Amazon EKS.
- **Imagen en Amazon ECR**: Repositorio `deposit` en la cuenta `881893826841` conservado intacto.
- **Infraestructura AWS**: Clúster EKS y VPC eliminados para garantizar **$0.00 USD de costo** mientras no estés trabajando.

---

## 2. Cómo Volver a Levantar la Infraestructura (El Día que Retomes)

Dado que todo el código, manifiestos y pipeline de CI/CD ya están listos y versionados en GitHub, volver a desplegar todo toma solo 2 pasos:

### Paso 1: Crear el Clúster EKS con `eksctl` (~15 minutos)
Abre tu terminal de PowerShell en esta carpeta y ejecuta:
```powershell
eksctl create cluster --name medio-curso-eks --region us-east-1 --version 1.34 --nodegroup-name workers --node-type m7i-flex.large --nodes 1 --zones us-east-1c,us-east-1f --profile eks-admin
```

### Paso 2: Habilitar el Acceso a GitHub Actions en EKS
Una vez que el clúster termine de crearse, dale permisos al rol de GitHub Actions para que pueda desplegar:
```powershell
aws eks create-access-entry --cluster-name medio-curso-eks --principal-arn arn:aws:iam::881893826841:role/github-actions-deposit-role --type STANDARD --profile eks-admin --region us-east-1

aws eks associate-access-policy --cluster-name medio-curso-eks --principal-arn arn:aws:iam::881893826841:role/github-actions-deposit-role --policy-arn arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy --access-scope type=cluster --profile eks-admin --region us-east-1
```

### Paso 3: Desplegar el Microservicio
Aplica los manifiestos de Kubernetes:
```powershell
kubectl apply -k k8s/
```
*(O simplemente haz un commit o re-ejecuta el workflow en GitHub Actions y el pipeline desplegará todo automáticamente).*

---

## 3. Tareas de Integración con tus Compañeros

### Opción 1: Abrir el Acceso Público para la Integración
Cuando los equipos de **Retiros**, **Billeteras** u otros canales vayan a invocar tu microservicio:
1. En `k8s/service.yaml`, verificar que el tipo sea `LoadBalancer`.
2. Para que cualquier compañero pueda conectarse, retira la sección `loadBalancerSourceRanges` o añade sus IPs públicas.
3. Aplica los cambios:
   ```powershell
   kubectl apply -f k8s/service.yaml
   ```
4. Tus compañeros consumirán los endpoints en: `http://<DNS_DEL_LOAD_BALANCER>/api/v1/deposits/usd`.

### Opción 2: Conectar con el Microservicio de Cuentas Real del Compañero
Cuando el compañero responsable de Cuentas tenga su endpoint listo en AWS (ej: `http://54.x.x.x:8081`):
1. Actualiza [k8s/configmap.yaml](file:///c:/Users/ThikPad/Desktop/MESE%20VIII/DESARROLLO%20DE%20APLICACIONES%20PARA%20LA%20NUBE/microservicios/microservicio/k8s/configmap.yaml):
   ```yaml
   ACCOUNTS_SERVICE_URL: "http://<IP_O_DNS_DEL_COMPAÑERO>:8081"
   ```
2. Sube el cambio a GitHub:
   ```powershell
   git add k8s/configmap.yaml
   git commit -m "chore: apuntar a microservicio de cuentas real del companero"
   git push origin main
   ```
