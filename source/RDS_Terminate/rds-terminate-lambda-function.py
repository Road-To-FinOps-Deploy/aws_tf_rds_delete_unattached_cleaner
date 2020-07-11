import boto3


def lambda_handler(event, context): 

    # Get list of regions
    ec2_client = boto3.client('ec2')
    regions = [region['RegionName']
               for region in ec2_client.describe_regions()['Regions']]

    # Iterate over each region
    for region in regions:
        #rds = boto3.resource('rds', region_name=region)
        rds_client = boto3.client('rds', region_name=region)
        print("Region:", region)

        # Get only running instances
        instances = rds_client.describe_db_instances()
        # Terminate the instances
        for instance in instances['DBInstances']:

            if instance['DBInstanceStatus'] == 'stopped':
                rds_client.delete_db_instance(
                    DBInstanceIdentifier=instance['DBInstanceIdentifier'], 
                    SkipFinalSnapshot=True
                )
                print('Terminate database instance: ', instance['DBInstanceIdentifier'])
