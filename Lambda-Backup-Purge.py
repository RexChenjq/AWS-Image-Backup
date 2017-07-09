import boto3
import collections
import datetime
import time
import sys
import botocore

ec2_client = boto3.client('ec2',region_name='ap-southeast-2')
ec2_resource = boto3.resource('ec2',region_name='ap-southeast-2')
sns = boto3.client('sns')
images_all = ec2_resource.images.filter(Owners=["self"]) # All AMIs belong to this account
timezone_offset = 11
today_fmt = (datetime.datetime.now()+ datetime.timedelta(hours=timezone_offset)).strftime('%Y-%m-%d')
today_date = time.strptime(today_fmt, '%Y-%m-%d')


def lambda_handler(event, context):
    try:
        images_to_remove=[]
        # List of all the instances that are being backed up
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
      
        toremoveimagecount = 0
        snapshotcount = 0

        for instance in instances:
            totalimagecount = 0
            backupSuccess = False
            for image in images_all:
                if (image.name.startswith('Lambda-') and image.name.find(instance['InstanceId']) > 0):
                    totalimagecount += 1
                    try:
                        if image.tags is not None:
                            deletion_date = [
                                t.get('Value') for t in image.tags
                                if t['Key'] == 'DeleteOn'][0]
                            delete_date = time.strptime(deletion_date, "%Y-%m-%d")
                    except IndexError:
                        deletion_date = False
                        delete_date = False                
                    if delete_date <= today_date:
                        images_to_remove.append(image.id)

                    # To make sure we have an AMI from today and mark backupSuccess as true
                    if image.name.endswith(today_fmt):
                        backupSuccess = True
                        print "Latest backup from " + today_fmt + " was a success"

            print "instance " + instance['InstanceId'] + " has " + str(totalimagecount) + " AMIs"
            print "============="
            print "About to deregister the following AMIs:"
            print images_to_remove
            if backupSuccess == True:
            # Only purge when the instance has a successful backup today 
                snapshots = ec2_client.describe_snapshots(OwnerIds=["self"])['Snapshots'] # All snapshots belong to this account
                for image in images_to_remove:
                    toremoveimagecount += 1
                    print "deregistering image %s" % image
                    amiResponse = ec2_client.deregister_image(
                        DryRun=False,
                        ImageId=image,
                    )
                    images_to_remove.remove(image)
    
                    for snapshot in snapshots:
                        if snapshot['Description'].find(image) > 0:
                            snapshotcount += 1
                            snap = ec2_client.delete_snapshot(SnapshotId=snapshot['SnapshotId'])
                            print "Deleting snapshot " + snapshot['SnapshotId']
                            print "-------------"
            else:
                print "No existing backup found. Purge for %s has been suspended" % instance['InstanceId']
        result = "Deleted %d AMIs and %d corresponding snapshots" %(toremoveimagecount,snapshotcount)
        print result
        #SNS email
        response = sns.publish(
        TopicArn='arn:aws:sns:ap-southeast-2:35213812****:lambda_ami_backup', # Replace **** with your own TopicArn
        Message= result,
        Subject='Purge Success')
       
    except botocore.exceptions.ClientError as e:
        result = e.response['Error']['Message']
        print result
        #SNS email
        response = sns.publish(
        TopicArn='arn:aws:sns:ap-southeast-2:35213812****:lambda_ami_backup', # Replace **** with your own TopicArn
        Message= result,
        Subject='Purge Failed')