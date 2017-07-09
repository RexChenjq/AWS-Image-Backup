# AWS-Image-Backup

A backup system built on AWS CloudWatch + Lambda + IAM + SNS written in Python.

How to run the system?

1. Tag the instances you want to back up with a tag pair "Backup":"True". 

2. Create an IAM role with the following permissions 
  - AmazonEC2FullAccess
  - AWSLambdaFullAccess
  - CloudWatchFullAccess
  - AmazonSNSFullAccess
  
3.Create 2 SNS topics and subscribe both topics using the email address to received notifications.
  Put the TopicArn into the code.

4.Create 2 AWS Lambda Functions exactly the same as two Python scripts listed in the project
Lambda-AMI-Backup.py
Lambda-Backup-Purge.py

5.Set a Cron job in Cloudwatch running every 12am to backup and another job running every 1am to purge. Set the cron jobs as triggers of the two Lambda functions
Take Sydney-Region for example 
- (00 13 ? * * * ) to backup
- (00 14 ? * * * ) to purge

6.Customise Lambda function configuration

My parameters are set to:
- Use the IAM role set in Step 2
- Set memory to 128mb
- Set timeout to 1 min

Note: Please test and optimise these 2 parameters based on your environment. The required running time will increase when the number of AMIs and Snapshots increase.





