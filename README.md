# AWS EC2 instance Reaper
Within EC2 there are quite some use cases for ephemeral ec2 instances: for batch jobs like Hashicorp Packer and
Gitlab autoscaling runners. However, sometimes these ephemeral instances are not stopped because errors in the
controlling process.

This utility stops or terminated all virtual machines which have the tags 'ExpiresAfter' and 'ExpirationAction'
set. 

| tag              | Description                                                 |
|------------------|-------------------------------------------------------------|
| ExpiresAfter     | duration after which the instance is considered expired     |
| ExpirationAction | action to take after the expiration time: terminate or stop |


You can use it as a command line utility or install it as an AWS Lambda function and stop the spend , NoOps style!

To make the utility work for hashicorp Packer, add a run_tags block to the Packer builder specification:

```hcl
source "amazon-ebs" "ubuntu" {
   name = "my_ubuntu"
   ...
   run_tags = {
     ExpiresAfter = "2h"
     ExpirationAction = "terminate"
   }
```

## install the ec2 instance reaper
to install the ec2 instance reaper, type:

```sh
pip install aws-ec2-instance-reaper
```

## show running ephemeral instances
To show running ephemeral instances:
```sh
$ aws-ec2-instance-reaper list

i-06ac951992dbc11a1 (Packer Builder) launched 13 minutes ago - terminated
i-035ebe427a538c829 (Packer Builder) launched 4 minutes ago - running
INFO: 2 emphemeral ec2 instances found
```
### usage with multiple profiles
If you have multiple AWS Profiles (e.g. when working with AWS Organisations and SSO) you can specify the profile 
to use on the command line before executing the `aws-ec2-instance-reaper`.

```sh
$ AWS_PROFILE=not-my-default-profile aws-ec2-instance-reaper list

i-0d72937e04c1123a9 (Packer Builder) launched 31 minutes ago - running
i-0712d9bd593adb2fb (Packer Builder) launched 11 minutes ago - running
INFO: 2 emphemeral ec2 instances found
```

## stop ephemeral instances
To stop running ephemeral instances which expired:
```sh
$ aws-ec2-instance-reaper stop

INFO: stopping i-035ebe427a538c829 (Packer Builder) created 2 hours ago
INFO: total of 1 running ephemeral instances stopped
```

## terminate ephemeral instances
To terminate stopped and running expired ephemeral instances
```sh
aws-ec2-instance-reaper --verbose terminate

INFO: terminating i-035ebe427a538c829 (Packer Builder) created 25 hours ago
INFO: total of 1 instances terminated
```

## deploy the ec2 instance reaper
To deploy the ec2 instance reaper as an AWS Lambda, type:

```sh
git clone https://github.com/binxio/aws-ec2-instance-reaper.git
cd aws-ec2-instance-reaper
aws cloudformation deploy \
	--capabilities CAPABILITY_IAM \
	--stack-name aws-ec2-instance-reaper \
	--template-file ./cloudformation/aws-ec2-instance-reaper.yaml
```
This will install the ec2 instance reaper in your AWS account and run every hour.
