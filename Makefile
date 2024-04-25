include Makefile.mk

NAME=aws-ec2-instance-reaper
AWS_REGION=eu-central-1
S3_BUCKET_PREFIX=binxio-public
S3_BUCKET=$(S3_BUCKET_PREFIX)-$(AWS_REGION)
ALL_REGIONS=$(shell aws --region $(AWS_REGION) \
                ec2 describe-regions            \
                --query 'join(`\n`, Regions[?RegionName != `$(AWS_REGION)`].RegionName)' \
                --output text)

help:           ## Show this help.
	@fgrep -h "##" $(MAKEFILE_LIST) | grep -v fgrep | sed -e 's/\([^:]*\):[^#]*##\(.*\)/printf '"'%-20s - %s\\\\n' '\1' '\2'"'/' |bash

do-push: deploy

do-build: target/$(NAME)-$(VERSION).zip

upload-dist:		## to pypi
	rm -f dist/*
	python -mbuild
	twine upload dist/*

target/$(NAME)-$(VERSION).zip: src/*/*.py setup.cfg pyproject.toml Dockerfile.lambda
	mkdir -p target
	docker build --build-arg ZIPFILE=$(NAME)-$(VERSION).zip -t $(NAME)-lambda:$(VERSION) -f Dockerfile.lambda . && \
		ID=$$(docker create $(NAME)-lambda:$(VERSION) /bin/true) && \
		docker export $$ID | (cd target && tar -xvf - $(NAME)-$(VERSION).zip) && \
		docker rm -f $$ID && \
		chmod ugo+r target/$(NAME)-$(VERSION).zip

clean:		## all intermediate files
	rm -rf target dist
	find . -name \*.pyc | xargs rm 

test:			## run unit tests
	tox run
	for i in $$PWD/cloudformation/*; do \
		aws cloudformation validate-template --template-body file://$$i > /dev/null || exit 1; \
	done

fmt:			## sources using black
	black src/ tests/

deploy: target/$(NAME)-$(VERSION).zip		## lambda zip to the region $(AWS_REGION)
	aws s3 --region $(AWS_REGION) \
		cp --acl \
		public-read target/$(NAME)-$(VERSION).zip \
		s3://$(S3_BUCKET)/lambdas/$(NAME)-$(VERSION).zip
	aws s3 --region $(AWS_REGION) \
		cp --acl public-read \
		s3://$(S3_BUCKET)/lambdas/$(NAME)-$(VERSION).zip \
		s3://$(S3_BUCKET)/lambdas/$(NAME)-latest.zip

deploy-all-regions: deploy ## lambda zip to all AWS regions
	@for REGION in $(ALL_REGIONS); do \
		echo "copying to region $$REGION.." ; \
		aws s3 --region $$REGION \
			cp --acl public-read \
			s3://$(S3_BUCKET_PREFIX)-$(AWS_REGION)/lambdas/$(NAME)-$(VERSION).zip \
			s3://$(S3_BUCKET_PREFIX)-$$REGION/lambdas/$(NAME)-$(VERSION).zip; \
		aws s3 --region $$REGION \
			cp  --acl public-read \
			s3://$(S3_BUCKET_PREFIX)-$$REGION/lambdas/$(NAME)-$(VERSION).zip \
			s3://$(S3_BUCKET_PREFIX)-$$REGION/lambdas/$(NAME)-latest.zip; \
	done


deploy-lambda:					## to your AWS account
	sed -i -e "s^lambdas/$(NAME).*\.zip^lambdas/$(NAME)-$(VERSION).zip^g" cloudformation/aws-ec2-instance-reaper.yaml
	aws cloudformation deploy \
		--capabilities CAPABILITY_IAM \
		--stack-name $(NAME) \
		--template-file ./cloudformation/aws-ec2-instance-reaper.yaml \
		--parameter-override \
		    LambdaS3Bucket=$(S3_BUCKET)

delete-lambda:					## from your AWS account
	aws cloudformation delete-stack --stack-name $(NAME)
	aws cloudformation wait stack-delete-complete  --stack-name $(NAME)

deploy-pipeline:				## to your AWS account
		aws cloudformation deploy \
		--capabilities CAPABILITY_IAM \
                --stack-name $(NAME)-pipeline \
                --template-file ./cloudformation/cicd-pipeline.yaml \
                --parameter-overrides \
                        S3BucketPrefix=$(S3_BUCKET_PREFIX)-$(AWS_REGION

delete-pipeline:				## from your AWS account
	aws cloudformation delete-stack --stack-name $(NAME)-pipeline
	aws cloudformation wait stack-delete-complete  --stack-name $(NAME)-pipeline


demo: 						## to your AWS account
	export VPC_ID=$$(aws ec2 --output text --query 'Vpcs[?IsDefault].VpcId' describe-vpcs) ; \
	export SUBNET_IDS=$$(aws ec2 --output text --query 'Subnets[*].SubnetId' \
                                describe-subnets --filters Name=vpc-id,Values=$$VPC_ID | tr '\t' ','); \
	echo "deploy $(NAME)-demo in default VPC $$VPC_ID, subnets $$SUBNET_IDS" ; \
        ([[ -z $$VPC_ID ]] || [[ -z $$SUBNET_IDS ]] ) && \
                echo "Either there is no default VPC in your account or there are no subnets in the default VPC" && exit 1 ; \
	aws cloudformation deploy --stack-name $(NAME)-demo \
		--template-file ./cloudformation/demo-stack.yaml  \
		--parameter-overrides 	VPC=$$VPC_ID Subnets=$$SUBNET_IDS


delete-demo:					## from your AWS account
	aws cloudformation delete-stack --stack-name $(NAME)-demo
	aws cloudformation wait stack-delete-complete  --stack-name $(NAME)-demo


make-bucket:							## to store the lambda zip file
	aws s3 mb $(S3_BUCKET) || echo "warning bucket already exists"
	aws s3api put-public-access-block --bucket $(S3_BUCKET) \
  	--public-access-block-configuration \
  	'BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false'
	aws s3api put-bucket-ownership-controls --bucket $(S3_BUCKET)\
  	--ownership-controls 'Rules=[{ObjectOwnership="BucketOwnerPreferred"}]'
