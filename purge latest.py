import boto3
import collections
import datetime
import time
import sys
import botocore

ec2_client = boto3.client('ec2',region_name='ap-southeast-2')
ec2_resource = boto3.resource('ec2',region_name='ap-southeast-2')
sns = boto3.client('sns')
images_all = ec2_resource.images.filter(Owners=["self"])
today_fmt = (datetime.datetime.now()+ datetime.timedelta(hours=11)).strftime('%Y-%m-%d')
today_date = time.strptime(today_fmt, '%Y-%m-%d')


def lambda_handler(event, context):
    try:
        images_to_remove=[]
        toremoveimagecount = 0
        snapshotcount = 0
        totalimagecount=0
        for image in images_all:
            if (image.name.startswith('Lambda-')):
                totalimagecount+=1
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
            
        print "============="
        print "About to deregister the following AMIs:"
        print images_to_remove 
        snapshots = ec2_client.describe_snapshots(OwnerIds=["self"])['Snapshots']
        for image in images_to_remove:
            toremoveimagecount += 1
            print "deregistering image %s" % image
            amiResponse = ec2_client.deregister_image(
                DryRun=False,
                ImageId=image,
            )
            for snapshot in snapshots:
                if snapshot['Description'].find(image) > 0:
                    snapshotcount += 1
                    snap = ec2_client.delete_snapshot(SnapshotId=snapshot['SnapshotId'])
                    print "Deleting snapshot " + snapshot['SnapshotId']
                    print "-------------"
        result = "Deleted %d AMIs and %d corresponding snapshots" %(toremoveimagecount,snapshotcount)
        print result
        response = sns.publish(
        TopicArn='arn:aws:sns:ap-southeast-2:352138128272:lambda_ami_backup',
        Message= result,
        Subject='Purge Success')
        #SNS email
    except botocore.exceptions.ClientError as e:
        result = e.response['Error']['Message']
        print result
        response = sns.publish(
        TopicArn='arn:aws:sns:ap-southeast-2:352138128272:lambda_ami_backup',
        Message= result,
        Subject='Purge Failed')
        #SNS email

