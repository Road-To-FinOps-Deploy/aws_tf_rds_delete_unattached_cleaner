#https://stackoverflow.com/questions/60567109/how-to-get-list-of-active-connections-on-rds-using-boto3
import datetime
import boto3
import os

class RDSTermination:
    #Strandard constructor for RDSTermination class
    def __init__(self, cloudwatch_object, rds_object):
        self.cloudwatch_object = cloudwatch_object
        self.rds_object = rds_object

    #Getter and setters for variables.
    @property
    def cloudwatch_object(self):
        return self._cloudwatch_object

    @cloudwatch_object.setter
    def cloudwatch_object(self, cloudwatch_object):
        self._cloudwatch_object = cloudwatch_object

    @property
    def rds_object(self):
        return self._rds_object

    @rds_object.setter
    def rds_object(self, rds_object):
        self._rds_object = rds_object

    # Fetch connections details for all the RDS instances.Filter the list and return
    # only those instances which are  having 0 connections at the time of this script run
    def _get_instance_connection_info(self):
        rds_instances_connection_details = {}

        response = self.cloudwatch_object.get_metric_data(
            MetricDataQueries=[
                {
                    'Id': 'fetching_data_for_something',
                    'Expression': "SEARCH('{AWS/RDS,DBInstanceIdentifier} MetricName=\"DatabaseConnections\"', 'Average', 300)",
                    'ReturnData': True
                },
            ],
            EndTime=datetime.datetime.utcnow(),
            StartTime=datetime.datetime.utcnow() - datetime.timedelta(hours=2),
            ScanBy='TimestampDescending',
            MaxDatapoints=123
        )
        # response is of type dictionary with MetricDataResults as key

        for instance_info in response['MetricDataResults']:
            if len(instance_info['Timestamps']) > 0:
                rds_instances_connection_details[instance_info['Label']] = instance_info['Values'][-1]
        return rds_instances_connection_details

    # Fetches list of all instances and there status.
    def _fetch_all_rds_instance_state(self):
        all_rds_instance_state = {}
        response = self.rds_object.describe_db_instances()
        instance_details = response['DBInstances']
        for instance in instance_details:
            all_rds_instance_state[instance['DBInstanceIdentifier']] = instance['DBInstanceStatus']
        return all_rds_instance_state

    # We further refine the list and remove instances which are stopped. We will work on
    # Instances with Available state only
    def _get_instance_allowed_for_deletion(self):
        instances = self._get_instance_connection_info()
        all_instance_state = self._fetch_all_rds_instance_state()
        instances_to_delete = []

        try:
            for instance_name in instances.keys():
                if instances[instance_name] == 0.0 and all_instance_state[instance_name] == 'available':
                    instances_to_delete.append(instance_name)
        except BaseException:
            print("Check if instance connection_info is empty")
        return instances_to_delete

    # Function to delete the instances reported in final list.It deletes instances with 0 connection
    # and status as available
    def terminate_rds_instances(self, run):
        dry_run=run
        if dry_run:
            message = 'DRY-RUN'
        else:
            message = 'DELETE'
        rdsnames = self._get_instance_allowed_for_deletion()
        if len(rdsnames) > 0:
            for rdsname in rdsnames:
                try:
                    response = self.rds_object.describe_db_instances(
                        DBInstanceIdentifier=rdsname
                    )
                    termination_protection = response['DBInstances'][0]['DeletionProtection']
                except BaseException as e:
                    print('[ERROR]: reading details' + str(e))
                    exit(1)

                if termination_protection is True:
                    try:
                        print("Removing delete termination for {}".format(rdsname))
                        if not dry_run:
                            response = self.rds_object.modify_db_instance(
                                DBInstanceIdentifier=rdsname,
                                DeletionProtection=False

                            )
                    except BaseException as e:
                        print(
                            "[ERROR]: Could not modify db termination  protection "
                            "due to following error:\n " + str(
                                e))
                        exit(1)
                try:
                    if not dry_run:
                        print("i got executed")
                        response = self.rds_object.delete_db_instance(
                            DBInstanceIdentifier=rdsname,
                            SkipFinalSnapshot=True,
                        )
                    print('[{}]: RDS instance {} deleted'.format(message, rdsname))

                except BaseException:
                    print("[ERROR]: {} rds instance not found".format(rdsname))
        else:
            print("No RDS instance marked for deletion")


if __name__ == "__main__":
    cloud_watch_object = boto3.client('cloudwatch', region_name='eu-west-1')
    rds_object = boto3.client('rds', region_name='eu-west-1')
    rds_termination_object = RDSTermination(cloud_watch_object, rds_object)
    run = os.environ['DRYRUN']#True
    rds_termination_object.terminate_rds_instances(run)

