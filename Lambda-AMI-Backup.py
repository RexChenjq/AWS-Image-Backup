# Author Rex Chen
#
# 1. Find all instances with a tag "Backup":"True" and put them into the list "to_tag"
# 2. Create AMIs for all instances
# 3. Create Tag "DeleteOn" based on retention policy and today's date
# 4. Send SNS email notifications


import boto3
import collections
import datetime
import botocore

ec2_client = boto3.client('ec2',region_name='ap-southeast-2')
sns = boto3.client('sns')
retention_days = 28 # Custmised retention 
timezone_offset = 11 # AEST timezone

def lambda_handler(event, context):
    try:
        # Get all instances in your AWS account in this region with a tag "Backup":"True".
        reservations = ec2_client.describe_instances(
            Filters=[
                {'Name': 'tag:Backup', 'Values': ['True']},
            ]
        ).get(
            'Reservations', []
        )
        
        instances = sum(
            [
                [i for i in r['Instances']]
                for r in reservations
            ], [])
    
        print "Found %d instances that need backing up" % len(instances)
        
        to_tag = [] # List of Image IDs to be tagged/ to be backed up
        # imageDone = [] 
        imageCount = 0

        delete_date = datetime.date.today() + datetime.timedelta(days=retention_days)
        delete_fmt = delete_date.strftime('%Y-%m-%d')

        if((datetime.datetime.today()+ datetime.timedelta(hours=timezone_offset)).day == 1): #If today is the first day of the month, change the Delete time tag to keep the backup forever
            delete_fmt = "9999-1-1"  

        for instance in instances:
            create_time = datetime.datetime.now()+ datetime.timedelta(hours=timezone_offset)
            create_fmt = create_time.strftime('%H.%M.%S.%Y-%m-%d')
            instance_name = [
                str(t.get('Value',"Empty")) for t in instance['Tags']
                if t['Key'] == 'Name'][0]
            #Create Image for those Instansed to be backup.   
            AMIid = ec2_client.create_image(InstanceId=instance['InstanceId'], Name="Lambda-"+ instance['InstanceId'] + "-" + instance_name +  "-From-" + create_fmt, Description="Lambda created AMI of instance " + instance['InstanceId'], NoReboot=True, DryRun=False)
            to_tag.append(AMIid['ImageId'])
            imageCount+=1
            print "Created AMI %s of instance %s " % (AMIid['ImageId'], instance['InstanceId'])
            )

        print "Will delete %d AMIs on %s" % (len(to_tag), delete_fmt)
        ec2_client.create_tags(
            Resources=to_tag,
            Tags=[
                {'Key': 'DeleteOn', 'Value': delete_fmt},# This tag will be used to control the purge function in the Lambda-Backup-Purge script
                {'Key': 'Client ID', 'Value': 'Replace It With Your ClientID'}, # Tag  client ID for billing purposes
            ]
        )

        # Push SNS notifications after the backup is completed.
        result = "Successfully created AMIs for %d instances" %imageCount
        print result
        response = sns.publish(
        TopicArn='arn:aws:sns:ap-southeast-2:35213812****:lambda_ami_backup', # Replace **** with your own TopicArn created in SNS
        Message= result,
        Subject='Backup Success')
    except botocore.exceptions.ClientError as e:
        result = e.response['Error']['Message']
        print result
        response = sns.publish(
        TopicArn='arn:aws:sns:ap-southeast-2:35213812****:lambda_ami_backup',# Replace **** with your own TopicArn created in SNS
        Message= result,
        Subject='Backup Failure')