# AWS-SecurityGroup-Auditor

#### Descripción

Este script está diseñado para realizar una auditoría completa de los grupos de seguridad (SGs) en una cuenta de AWS, verificando la asociación de cada SG con diversos recursos dentro de la nube de AWS. La finalidad de esta auditoría es identificar los SGs que no están siendo utilizados por ningún recurso y ofrecer la opción de eliminarlos, lo que contribuye a la limpieza y optimización de la infraestructura en la nube.

#### Requisitos

- Python 3.x
- Boto3
- Credenciales de AWS configuradas correctamente (pueden ser mediante variables de entorno, archivos de configuración, roles de IAM, etc.)

#### Cómo usar

1. **Configuración del Ambiente**: Asegúrate de que Python y Boto3 están instalados y que tus credenciales de AWS están configuradas correctamente.
2. **Ejecución del Script**: Ejecuta el script utilizando Python desde la línea de comandos:
   ```
   python script_sg_audit.py
   ```
3. **Interacción durante la Ejecución**: El script te solicitará confirmación antes de proceder a eliminar los grupos de seguridad que no estén asociados a ningún recurso. Debes responder `sí` para proceder con la eliminación.

#### Funcionalidades Clave

- **Creación de Clientes Boto3**: El script inicializa clientes para varios servicios de AWS (EC2, ELB, RDS, ECS, EKS, entre otros) necesarios para la auditoría.
- **Obtención del ID de la Cuenta de AWS**: Utiliza el servicio STS para obtener el ID de la cuenta y crear un nombre de archivo de log basado en este.
- **Listado y Revisión de Grupos de Seguridad**: Enumera todos los grupos de seguridad y verifica su asociación con una amplia gama de recursos de AWS, incluyendo instancias EC2, balances de carga, bases de datos RDS, clústeres EKS y ECS, y más.
- **Registro de Actividades**: Todas las acciones y hallazgos se registran tanto en la consola como en un archivo de log, facilitando su revisión posterior.
- **Identificación de SGs no Asociados**: Al final de la ejecución, el script identifica los SGs que no están asociados a ningún recurso y ofrece la opción de eliminarlos.

#### Consideraciones

- Este script realiza cambios activos (como la eliminación de SGs) basados en la interacción del usuario. Debe ser ejecutado por un usuario con permisos adecuados y con precaución.
- Aunque el script cubre una amplia gama de servicios de AWS, la configuración específica de tu entorno puede requerir ajustes o la inclusión de servicios adicionales.
- La eliminación de grupos de seguridad no puede deshacerse. Asegúrate de revisar el archivo de log y confirmar las acciones antes de proceder con la eliminación.

#### Soporte

Para cualquier duda o problema con la ejecución del script, revisa la documentación oficial de Boto3 o busca ayuda en las comunidades de AWS y Python.

Este script es una herramienta poderosa para la gestión y optimización de la seguridad en AWS, asegurando que solo los recursos necesarios estén protegidos por grupos de seguridad y ayudando a mantener la configuración de la red organizada y segura.
