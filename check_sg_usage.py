import boto3
import sys

# Función para escribir mensajes tanto en el archivo de log como en la consola
def print_both(message, file):
    print(message)
    print(message, file=file)

# Crear clientes para los servicios de EC2, ELB, ELBv2 (ALB/NLB), RDS, y otros que necesites.
ec2 = boto3.client('ec2')
elb = boto3.client('elb')
elbv2 = boto3.client('elbv2')
rds = boto3.client('rds')
ecs = boto3.client('ecs')
eks = boto3.client('eks')
codebuild = boto3.client('codebuild')
redshift = boto3.client('redshift')
elasticache = boto3.client('elasticache')
kafka = boto3.client('kafka')
neptune = boto3.client('neptune')
docdb = boto3.client('docdb')
elasticbeanstalk = boto3.client('elasticbeanstalk')
sagemaker = boto3.client('sagemaker')
transfer = boto3.client('transfer')
glue = boto3.client('glue')
es = boto3.client('es')
mq = boto3.client('mq')
fsx = boto3.client('fsx')
workspaces = boto3.client('workspaces')
# Y así sucesivamente para otros servicios que requieras.

# Obtener el ID de la cuenta de AWS
sts = boto3.client('sts')
account_id = sts.get_caller_identity()["Account"]

# Guardamos la salida del script en un fichero de log
output_file = f"{account_id}_sg_log.txt"


# Inicializar un diccionario para rastrear las asociaciones de SGs
asociaciones_sg = "{sg['GroupId']: False for sg in security_groups}"


with open(output_file, 'w') as log_file:
    # Usando la función personalizada para imprimir
    print_both(f"\nVerificación de uso de grupos de seguridad para la cuenta AWS: {account_id}", log_file)
    
    # Lista todos los grupos de seguridad y sus descripciones
    security_groups = ec2.describe_security_groups()['SecurityGroups']

    # Inicializar un diccionario para rastrear las asociaciones de SGs
    asociaciones_sg = {sg['GroupId']: False for sg in security_groups}


    # Antes de iniciar el bucle de los grupos de seguridad, calcula el total
    total_security_groups = len(security_groups)

    # Inicializa un contador antes de comenzar el bucle
    current_sg_number = 0

    for sg in security_groups:
        current_sg_number += 1  # Incrementa el contador para cada grupo de seguridad
        sg_id = sg['GroupId']
        sg_description = sg['Description']
        print_both("------------------------------------------------", log_file)
        print_both(f"Revisando el grupo de seguridad ({current_sg_number}/{total_security_groups}): {sg_id} ({sg_description})", log_file)
        
        # Continuar con la lógica para cada grupo de seguridad
        # Por ejemplo, listar instancias EC2 asociadas a cada SG
        instances = ec2.describe_instances(
            Filters=[
                {'Name': 'instance.group-id', 'Values': [sg_id]}
            ]
        )['Reservations']
        if instances:
            for reservation in instances:
                for instance in reservation['Instances']:
                    print_both(f"\tInstancia EC2 asociada: {instance['InstanceId']}, Estado: {instance['State']['Name']}", log_file)
                    asociaciones_sg[sg_id] = True
        # Lista de ELBs (Elastic Load Balancers) clásicos asociados al grupo de seguridad
        elbs = elb.describe_load_balancers()['LoadBalancerDescriptions']
        for elb_desc in elbs:
            if sg_id in elb_desc.get('SecurityGroups', []):
                print_both(f"\tELB Clásico Asociado: {elb_desc['LoadBalancerName']}", log_file)
                asociaciones_sg[sg_id] = True

        # Lista de ELBv2 (ALB/NLB) asociados al grupo de seguridad
        elbv2_load_balancers = elbv2.describe_load_balancers()['LoadBalancers']
        for lb in elbv2_load_balancers:
            if sg_id in lb.get('SecurityGroups', []):
                print_both(f"\tALB/NLB Asociado: {lb['LoadBalancerName']}", log_file)
                asociaciones_sg[sg_id] = True

        # Lista de instancias RDS asociadas al grupo de seguridad
        dbs = rds.describe_db_instances()['DBInstances']
        for db in dbs:
            sg_found = False
            for sg in db['VpcSecurityGroups']:
                if sg_id == sg['VpcSecurityGroupId']:
                    sg_found = True
                    break
            if sg_found:
                print_both(f"\tInstancia RDS Asociada: {db['DBInstanceIdentifier']}", log_file)
                asociaciones_sg[sg_id] = True

        # AWS ECS - Verificar servicios de Amazon Elastic Container Service asociados al grupo de seguridad
        clusters = ecs.list_clusters()['clusterArns']
        for cluster_arn in clusters:
            next_token = None
            while True:
                if next_token:
                    service_list_response = ecs.list_services(cluster=cluster_arn, nextToken=next_token)
                else:
                    service_list_response = ecs.list_services(cluster=cluster_arn)
                service_arns = service_list_response['serviceArns']
                
                # Si no hay servicios, salir del bucle
                if not service_arns:
                    break

                # AWS ECS describe_services puede manejar solo 10 ARNs a la vez
                for i in range(0, len(service_arns), 10):
                    service_chunk = service_arns[i:i+10]
                    detailed_services_response = ecs.describe_services(
                        cluster=cluster_arn, 
                        services=service_chunk
                    )
                    for service in detailed_services_response['services']:
                        network_configuration = service.get('networkConfiguration', {})
                        awsvpc_configuration = network_configuration.get('awsvpcConfiguration', {})
                        security_groups = awsvpc_configuration.get('securityGroups', [])
                        if sg_id in security_groups:
                            print_both(f"\tECS Servicio Asociado: {service['serviceName']} en Cluster: {cluster_arn}", log_file)
                            asociaciones_sg[sg_id] = True

                # Manejar la paginación con nextToken
                next_token = service_list_response.get('nextToken')
                if not next_token:
                    break  # No más servicios para procesar


        # EKS - Clústeres de Amazon Elastic Kubernetes Service y nodos de trabajo asociados al grupo de seguridad
        eks_clusters = eks.list_clusters()['clusters']
        for cluster_name in eks_clusters:
            nodegroups = eks.list_nodegroups(clusterName=cluster_name)['nodegroups']
            for nodegroup_name in nodegroups:
                nodegroup = eks.describe_nodegroup(clusterName=cluster_name, nodegroupName=nodegroup_name)
                nodegroup_sg_ids = nodegroup['nodegroup']['resources']['clusterSecurityGroupId']
                if sg_id == nodegroup_sg_ids:
                    print_both(f"\tEKS Clúster: {cluster_name}, Grupo de Nodos: {nodegroup_name}, SG Asociado: {sg_id}", log_file)
                    asociaciones_sg[sg_id] = True


        # CodeBuild - Proyectos de AWS CodeBuild asociados al grupo de seguridad
        codebuild_projects = codebuild.list_projects()['projects']
        for project_name in codebuild_projects:
            project = codebuild.batch_get_projects(names=[project_name])['projects'][0]
            vpc_config = project.get('vpcConfig', {})
            sg_ids = vpc_config.get('securityGroupIds', [])
            if sg_id in sg_ids:
                print_both(f"\tProyecto CodeBuild Asociado: {project_name}", log_file)
                asociaciones_sg[sg_id] = True


        # Redshift - Clústeres de Amazon Redshift asociados al grupo de seguridad
        redshift_clusters = redshift.describe_clusters()['Clusters']
        for cluster in redshift_clusters:
            for vpc_sg in cluster['VpcSecurityGroups']:
                if sg_id == vpc_sg['VpcSecurityGroupId']:
                    print_both(f"\tClúster Redshift Asociado: {cluster['ClusterIdentifier']}", log_file)
                    asociaciones_sg[sg_id] = True


        # Amazon ElastiCache - Instancias de ElastiCache asociadas al grupo de seguridad
        cache_clusters = elasticache.describe_cache_clusters(ShowCacheNodeInfo=True)['CacheClusters']
        for cluster in cache_clusters:
            for sg in cluster['SecurityGroups']:
                if sg_id == sg['SecurityGroupId']:
                    print_both(f"\tInstancia ElastiCache Asociada: {cluster['CacheClusterId']}", log_file)
                    asociaciones_sg[sg_id] = True

        # Amazon MSK - Clústeres de Kafka asociados al grupo de seguridad
        kafka_clusters = kafka.list_clusters()['ClusterInfoList']
        for cluster in kafka_clusters:
            for sg in cluster['BrokerNodeGroupInfo']['SecurityGroups']:
                if sg_id == sg:
                    print_both(f"\tClúster Kafka Asociado: {cluster['ClusterName']}", log_file)
                    asociaciones_sg[sg_id] = True

        # Amazon Neptune - Instancias de bases de datos Neptune asociadas al grupo de seguridad
        neptune_instances = neptune.describe_db_instances()['DBInstances']
        for instance in neptune_instances:
            for sg in instance['VpcSecurityGroups']:
                if sg_id == sg['VpcSecurityGroupId']:
                    print_both(f"\tInstancia Neptune Asociada: {instance['DBInstanceIdentifier']}", log_file)
                    asociaciones_sg[sg_id] = True

        # Amazon DocumentDB - Clústeres de DocumentDB asociados al grupo de seguridad
        docdb_clusters = docdb.describe_db_clusters()['DBClusters']
        for cluster in docdb_clusters:
            for sg in cluster['VpcSecurityGroupIds']:
                if sg_id == sg:
                    print_both(f"\tClúster DocumentDB Asociado: {cluster['DBClusterIdentifier']}", log_file)
                    asociaciones_sg[sg_id] = True


        # Amazon Elastic Beanstalk - Entornos asociados al grupo de seguridad
        eb_environments = elasticbeanstalk.describe_environments()['Environments']
        for env in eb_environments:
            # Elastic Beanstalk no provee directamente los grupos de seguridad en la descripción del entorno,
            # así que este paso puede requerir obtener los recursos asociados al entorno y verificar sus grupos de seguridad de forma indirecta.
            # Esta es una aproximación simplificada.
            resources = elasticbeanstalk.describe_environment_resources(EnvironmentId=env['EnvironmentId'])['EnvironmentResources']
            instances = resources.get('Instances', [])
            for instance in instances:
                ec2_instance = ec2.describe_instances(InstanceIds=[instance['Id']])['Reservations'][0]['Instances'][0]
                for sg in ec2_instance['SecurityGroups']:
                    if sg_id == sg['GroupId']:
                        print_both(f"\tEntorno Elastic Beanstalk Asociado: {env['EnvironmentName']} ({env['EnvironmentId']})", log_file)
                        asociaciones_sg[sg_id] = True
                        break

        # Amazon SageMaker - Endpoints de SageMaker asociados al grupo de seguridad
        sm_endpoints = sagemaker.list_endpoints()['Endpoints']
        for endpoint in sm_endpoints:
            endpoint_desc = sagemaker.describe_endpoint(EndpointName=endpoint['EndpointName'])
            vpc_config = endpoint_desc.get('EndpointConfig', {}).get('VpcConfig', {})
            sg_ids = vpc_config.get('SecurityGroupIds', [])
            if sg_id in sg_ids:
                print_both(f"\tEndpoint de SageMaker Asociado: {endpoint['EndpointName']}", log_file)
                asociaciones_sg[sg_id] = True

        # AWS Transfer Family - Servidores asociados al grupo de seguridad
        # AWS Transfer Family no provee una forma directa de filtrar por grupos de seguridad mediante su operación de listado.
        # Podrías necesitar revisar los servidores individualmente y verificar sus configuraciones de VPC para asociar los grupos de seguridad.
        # Este código es un esbozo general y puede requerir ajustes basados en tus necesidades específicas.
        transfer_servers = transfer.list_servers()['Servers']
        for server in transfer_servers:
            server_id = server['ServerId']
            server_details = transfer.describe_server(ServerId=server_id)['Server']
            endpoint_details = server_details.get('EndpointDetails', {})
            if 'VpcEndpointId' in endpoint_details:  # Verificación simplificada; ajustar según la configuración exacta
                vpc_config = ec2.describe_vpc_endpoints(VpcEndpointIds=[endpoint_details['VpcEndpointId']])['VpcEndpoints'][0]
                for sg in vpc_config['Groups']:
                    if sg_id == sg['GroupId']:
                        print_both(f"\tServidor AWS Transfer Family Asociado: {server_id}", log_file)
                        asociaciones_sg[sg_id] = True
                        break


        # AWS Glue - Trabajos de Glue asociados al grupo de seguridad
        glue_jobs = glue.get_jobs()['Jobs']
        for job in glue_jobs:
            job_name = job['Name']
            connections = job.get('Connections', {}).get('Connections', [])
            for connection_name in connections:
                connection_info = glue.get_connection(Name=connection_name)['Connection']
                connection_sg_ids = connection_info['PhysicalConnectionRequirements'].get('SecurityGroupIdList', [])
                if sg_id in connection_sg_ids:
                    print_both(f"\tTrabajo de Glue Asociado: {job_name}", log_file)
                    asociaciones_sg[sg_id] = True


        # Amazon Elasticsearch Service (Amazon ES) - Dominios de ES asociados al grupo de seguridad
        es_domains = es.list_domain_names()['DomainNames']
        for domain_info in es_domains:
            domain_name = domain_info['DomainName']
            domain_config = es.describe_elasticsearch_domain(DomainName=domain_name)['DomainStatus']
            domain_sg_ids = domain_config.get('VPCOptions', {}).get('SecurityGroupIds', [])
            if sg_id in domain_sg_ids:
                print_both(f"\tDominio de Elasticsearch Asociado: {domain_name}", log_file)
                asociaciones_sg[sg_id] = True


        # VPN (Site-to-Site VPN Connections) - Conexiones VPN asociadas al grupo de seguridad
        vpn_connections = ec2.describe_vpn_connections()['VpnConnections']
        for vpn_connection in vpn_connections:
            # Este ejemplo asume que la configuración de seguridad para las VPN se relaciona indirectamente a través de las VPC o Customer Gateways y puede necesitar ajustes específicos
            # para tu configuración.
            if vpn_connection['State'] == 'available':
                customer_gateway_id = vpn_connection['CustomerGatewayId']
                customer_gateway = ec2.describe_customer_gateways(CustomerGatewayIds=[customer_gateway_id])['CustomerGateways'][0]
                if 'Tags' in customer_gateway and any(tag['Key'] == 'SecurityGroupId' and tag['Value'] == sg_id for tag in customer_gateway['Tags']):
                    print_both(f"\tConexión VPN Site-to-Site Asociada: {vpn_connection['VpnConnectionId']}", log_file)
                    asociaciones_sg[sg_id] = True

        # Amazon MQ - Brokers de Amazon MQ asociados al grupo de seguridad
        mq_brokers = mq.list_brokers()['BrokerSummaries']
        for broker_summary in mq_brokers:
            broker = mq.describe_broker(BrokerId=broker_summary['BrokerId'])['BrokerInstances']
            for instance in broker:
                for sg in instance['SecurityGroups']:
                    if sg_id == sg:
                        print_both(f"\tBroker de Amazon MQ Asociado: {broker_summary['BrokerName']}", log_file)
                        asociaciones_sg[sg_id] = True

        # Amazon FSx - Sistemas de archivos Amazon FSx asociados al grupo de seguridad
        fsx_file_systems = fsx.describe_file_systems()['FileSystems']
        for file_system in fsx_file_systems:
            for sg in file_system['VpcSecurityGroupIds']:
                if sg_id == sg:
                    print_both(f"\tSistema de archivos Amazon FSx Asociado: {file_system['FileSystemId']}", log_file)
                    asociaciones_sg[sg_id] = True

        # Amazon WorkSpaces - Directorios de Amazon WorkSpaces asociados al grupo de seguridad
        workspaces_directories = workspaces.describe_workspace_directories()['Directories']
        for directory in workspaces_directories:
            if 'WorkspaceSecurityGroupId' in directory and sg_id == directory['WorkspaceSecurityGroupId']:
                print_both(f"\tDirectorio Amazon WorkSpaces Asociado: {directory['DirectoryId']}", log_file)
                asociaciones_sg[sg_id] = True

        # Verificar VPC Endpoints asociados al grupo de seguridad
        vpc_endpoints = ec2.describe_vpc_endpoints()['VpcEndpoints']
        for vpc_endpoint in vpc_endpoints:
            if sg_id in vpc_endpoint.get('Groups', []):
                print_both(f"\tVPC Endpoint con SG: {vpc_endpoint['VpcEndpointId']}", log_file)
                asociaciones_sg[sg_id] = True

        # Verificar si el SG está siendo referenciado por otros SGs
        security_groups = ec2.describe_security_groups()['SecurityGroups']
        referenced_by_sgs = []

        for sg in security_groups:
            for perm in sg.get('IpPermissions', []) + sg.get('IpPermissionsEgress', []):
                for user_id_group_pair in perm.get('UserIdGroupPairs', []):
                    if user_id_group_pair['GroupId'] == sg_id:
                        referenced_by_sgs.append(sg['GroupId'])
                        break

        if referenced_by_sgs:
            referenced_by_sgs_str = ', '.join(referenced_by_sgs)
            print_both(f"\tReferenciado por otros SGs: {referenced_by_sgs_str}", log_file)
            asociaciones_sg[sg_id] = True
        
        print_both(f"\n", log_file)

    print_both(f"Proceso completado.", log_file)




    # Suponiendo que añadiste un diccionario al comienzo del script para rastrear las asociaciones
    # por ejemplo, asociaciones_sg = {sg_id: False for sg in security_groups}

    # Identificar SGs sin asociaciones
    sgs_sin_asociaciones = [sg_id for sg_id, tiene_asociaciones in asociaciones_sg.items() if not tiene_asociaciones]

    print_both("\n***RESULTADO***", log_file)
    if sgs_sin_asociaciones:
        
        print_both(f"\nLos siguientes grupos de seguridad no tienen recursos asociados: {', '.join(sgs_sin_asociaciones)}", log_file)
        respuesta = input("\n¿Quieres borrar estos grupos de seguridad? (sí/no): ")
        if respuesta.lower() in ['sí', 's', 'si', 'yes', 'y']:
            for sg_id in sgs_sin_asociaciones:
                try:
                    ec2.delete_security_group(GroupId=sg_id)
                    print(f"Grupo de seguridad {sg_id} borrado exitosamente.\n")
                except Exception as e:
                    print(f"Error al borrar el grupo de seguridad {sg_id}: {e}")
        else:
            print("\nNo se ha borrado ningun grupo de seguridad.\n")
    else:
        print("\nTodos los grupos de seguridad tienen recursos asociados.\n")
log_file.close()
