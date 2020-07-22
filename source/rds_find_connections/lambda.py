#https://stackoverflow.com/questions/60567109/how-to-get-list-of-active-connections-on-rds-using-boto3
import datetime
import boto3
from botocore.exceptions import ClientError
import os
import logging
from io import StringIO
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

log = logging.getLogger()

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
    def terminate_rds_instances(self, run, region):
        delete_list = []
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
                    
                    print('[{}]: RDS instance {} deleted in {}'.format(message, rdsname, region))
                    delete_list.append('[{}]: RDS instance {} deleted in {}'.format(message, rdsname, region))

                except BaseException:
                    print("[ERROR]: {} rds instance not found in {}".format(rdsname, region))
        else:
            print(f"No RDS instance marked for deletion in {region}")
        return delete_list

def email(reciver_email, sender_email, region, messege_content):
    messege = build_email(
        "RDS With No Connections",reciver_email, sender_email, body=f"{messege_content}"
    )  # subject, to, from, text
    try:
        send_email(messege, region)
        print("run email")

    except BaseException as e:
        print(e)



def build_email(subject, to_email, from_email, body=None, attachments={}):
    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["To"] = ",".join(to_email) if isinstance(to_email, list) else to_email
    msg["From"] = from_email

    if body and isinstance(body, dict):
        textual_message = MIMEMultipart("alternative")
        for m_type, message in body.items():
            part = MIMEText(message, m_type)
            textual_message.attach(part)
        msg.attach(textual_message)
    elif body and isinstance(body, str):
        msg.attach(MIMEText(body))

    if attachments:
        for filename, data in attachments.items():
            att = MIMEApplication(data)
            att.add_header("Content-Disposition", "attachment", filename=filename)
            msg.attach(att)

    return msg


def send_email(msg, region, session=boto3):
    ses = session.client("ses", region_name=region)
    try:
        response = ses.send_raw_email(
            Source=msg["From"],
            Destinations=msg["To"].split(","),
            RawMessage={"Data": msg.as_string()},
        )
    except ClientError as e:
        log.error(e.response["Error"]["Message"])
    else:
        id = response["MessageId"]
        log.info(f"Email sent! Message ID: {id}")




def lambda_handler(event, context):
    dryrun = os.environ['DRYRUN']#True
    email_region = os.environ['REGION']
    reciver_email = os.environ['RECIVER_EMAIL']
    sender_email = os.environ['SENDER_EMAIL']

    email_data = []
    # Get list of regions
    ec2_client = boto3.client('ec2')
    regions = [region['RegionName']
               for region in ec2_client.describe_regions()['Regions']] # need to add option to pass in one region

    # Iterate over each region
    for region in regions:
        cloud_watch_object = boto3.client('cloudwatch', region_name=region)
        rds_object = boto3.client('rds', region_name=region)
        rds_termination_object = RDSTermination(cloud_watch_object, rds_object)
        delete_list= rds_termination_object.terminate_rds_instances(dryrun, region)
        if delete_list != []:
            email_data.append(delete_list)
    print("this is the email")
    email(reciver_email, sender_email, email_region, email_data)

