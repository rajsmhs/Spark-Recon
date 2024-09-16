# Configure the AWS Provider
provider "aws" {
  region = var.aws_region
}



#Retrieve the list of AZs in the current AWS region
data "aws_availability_zones" "available" {}
data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

locals {
  team               = "GCC-Data-Analytics"
  application        = "ZETA"
  server_name        = "ec2-${var.environment}-api-${var.aws_region}"
  Region             = data.aws_region.current.name
  domain_name        = "ran-opensearch"
  lambda_opensearch  = "Write-To-OpenSearch"
  lambda_rule_engine = "business-rule-engine"
  lambda_sf_trigger  = "lambda-sf-trigger"

}

resource "random_password" "password" {
  length  = (2 + 12 + 3 + 0)
  special = false
}


#Define the VPC
resource "aws_vpc" "vpc" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = var.vpc_name
    Environment = var.environment
    team        = local.team
    application = local.application
    Terraform   = "true"
    Region      = local.Region
  }
}

#Deploy the private subnets
resource "aws_subnet" "private_subnets" {
  for_each   = var.private_subnets
  vpc_id     = aws_vpc.vpc.id
  cidr_block = cidrsubnet(var.vpc_cidr, 8, each.value)
  #availability_zone = tolist(data.aws_availability_zones.available.names)[each.value]
  availability_zone = ["${var.aws_region}a", "${var.aws_region}b", "${var.aws_region}c"][each.value - 1]


  tags = {
    Name        = each.key
    Terraform   = "true"
    Environment = var.environment
    team        = local.team
    application = local.application
    Terraform   = "true"
    Region      = local.Region

  }
}



#Deploy the public subnets
resource "aws_subnet" "public_subnets" {
  for_each   = var.public_subnets
  vpc_id     = aws_vpc.vpc.id
  cidr_block = cidrsubnet(var.vpc_cidr, 8, each.value + 100)
  #availability_zone = tolist(data.aws_availability_zones.available.names)[each.value]
  availability_zone       = ["${var.aws_region}a", "${var.aws_region}b", "${var.aws_region}c"][each.value - 1]
  map_public_ip_on_launch = true

  tags = {
    Name        = each.key
    Terraform   = "true"
    Environment = var.environment
    team        = local.team
    application = local.application
    Terraform   = "true"
    Region      = local.Region
  }
}

#Create route tables for public and private subnets
resource "aws_route_table" "public_route_table" {
  vpc_id = aws_vpc.vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.internet_gateway.id
    #nat_gateway_id = aws_nat_gateway.nat_gateway.id
  }
  tags = {
    Name        = "demo_public_rtb"
    Terraform   = "true"
    Environment = var.environment
    team        = local.team
    application = local.application
    Terraform   = "true"
    Region      = local.Region
  }
}

resource "aws_route_table" "private_route_table" {
  vpc_id = aws_vpc.vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    # gateway_id     = aws_internet_gateway.internet_gateway.id
    nat_gateway_id = aws_nat_gateway.nat_gateway.id
  }
  tags = {
    Name        = "demo_private_rtb"
    Terraform   = "true"
    Environment = var.environment
    team        = local.team
    application = local.application
    Terraform   = "true"
    Region      = local.Region
  }
}

#Create route table associations depends_on is used in the scenario if a resource block is dependent on other resource block
resource "aws_route_table_association" "public" {
  depends_on     = [aws_subnet.public_subnets]
  route_table_id = aws_route_table.public_route_table.id
  for_each       = aws_subnet.public_subnets
  subnet_id      = each.value.id

}

resource "aws_route_table_association" "private" {
  depends_on     = [aws_subnet.private_subnets]
  route_table_id = aws_route_table.private_route_table.id
  for_each       = aws_subnet.private_subnets
  subnet_id      = each.value.id
}

#Create Internet Gateway
resource "aws_internet_gateway" "internet_gateway" {
  vpc_id = aws_vpc.vpc.id
  tags = {
    Name        = "demo_igw"
    Environment = var.environment
    team        = local.team
    application = local.application
    Terraform   = "true"
    Region      = local.Region
  }
}

#Create EIP for NAT Gateway
resource "aws_eip" "nat_gateway_eip" {
  domain     = "vpc"
  depends_on = [aws_internet_gateway.internet_gateway]
  tags = {
    Name        = "demo_igw_eip"
    Environment = var.environment
    team        = local.team
    application = local.application
    Terraform   = "true"
    Region      = local.Region
  }
}

#Create NAT Gateway
resource "aws_nat_gateway" "nat_gateway" {
  depends_on    = [aws_subnet.public_subnets]
  allocation_id = aws_eip.nat_gateway_eip.id
  subnet_id     = aws_subnet.public_subnets["public_subnet_1"].id
  tags = {
    Name        = "demo_nat_gateway"
    Environment = var.environment
    team        = local.team
    application = local.application
    Terraform   = "true"
    Region      = local.Region
  }
}


resource "aws_vpc_endpoint" "vpc_endpoint_gw_s3" {
  vpc_id          = aws_vpc.vpc.id
  service_name    = "com.amazonaws.${var.aws_region}.s3"
  route_table_ids = [aws_route_table.public_route_table.id]
  tags = {
    Name        = "vpc_endpoint_gw_s3"
    Environment = var.environment
    team        = local.team
    application = local.application
    Terraform   = "true"
    Region      = local.Region
  }
}

resource "aws_vpc_endpoint" "vpc_endpoint_inf_kinesis" {
  vpc_id            = aws_vpc.vpc.id
  service_name      = "com.amazonaws.${var.aws_region}.kinesis-streams"
  vpc_endpoint_type = "Interface"

  security_group_ids = [
    aws_security_group.my-new-security-group.id,
  ]
  subnet_ids          = [aws_subnet.public_subnets["public_subnet_1"].id, aws_subnet.public_subnets["public_subnet_2"].id, aws_subnet.public_subnets["public_subnet_3"].id]
  private_dns_enabled = true
  tags = {
    Name        = "vpc_endpoint_inf_kinesis"
    Environment = var.environment
    team        = local.team
    application = local.application
    Terraform   = "true"
    Region      = local.Region
  }
}

resource "aws_vpc_endpoint" "vpc_endpoint_lambda" {
  vpc_id            = aws_vpc.vpc.id
  service_name      = "com.amazonaws.${var.aws_region}.lambda"
  vpc_endpoint_type = "Interface"

  security_group_ids = [
    aws_security_group.my-new-security-group.id,
  ]
  subnet_ids          = [aws_subnet.public_subnets["public_subnet_1"].id, aws_subnet.public_subnets["public_subnet_2"].id, aws_subnet.public_subnets["public_subnet_3"].id]
  private_dns_enabled = true
  tags = {
    Name        = "vpc_endpoint_lambda"
    Environment = var.environment
    team        = local.team
    application = local.application
    Terraform   = "true"
    Region      = local.Region
  }
}


resource "aws_s3_bucket" "my-new-S3-bucket" {
  bucket        = "my-new-tf-test-bucket-${random_id.randomness.hex}"
  force_destroy = false
  lifecycle {
    prevent_destroy = false
  }
  tags = {
    Name        = "my-new-tf-test-bucket-${random_id.randomness.hex}"
    Purpose     = "Intro to Resource Blocks Lab"
    Environment = var.environment
    team        = local.team
    application = local.application
    Terraform   = "true"
    Region      = local.Region
  }
}

#s3 bucket configuration
resource "aws_s3_bucket_ownership_controls" "my_new_bucket_acl" {
  bucket = aws_s3_bucket.my-new-S3-bucket.id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }

}

resource "random_id" "randomness" {
  byte_length = 16
}

#security group configuration
resource "aws_security_group" "my-new-security-group" {
  name        = "web_server_inbound"
  description = "Allow inbound traffic on tcp/443"
  vpc_id      = aws_vpc.vpc.id


  ingress {
    description = "Allow 2181 from the Internet"
    from_port   = 2181
    to_port     = 2181
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }

  ingress {
    description = "Allow 9092 from the Internet"
    from_port   = 9092
    to_port     = 9094
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }

  ingress {
    description = "Allow all traffic from self refrencing security group"
    from_port   = 0
    to_port     = 0
    protocol    = "All"
    self        = true
  }

  ingress {
    prefix_list_ids = ["pl-60b85b09"]
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
  }

  /*
  ingress {
    description = "Allow HTTP from the anywhere"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Allow HTTPs from the anywhere"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }*/



  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "All"
    cidr_blocks = ["0.0.0.0/0"]
    #ipv6_cidr_blocks = ["::/0"]
  }
  // Terraform removes the default rule
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "web_server_inbound"
    Purpose     = "Intro to Resource Blocks Lab"
    Environment = var.environment
    team        = local.team
    application = local.application
    Terraform   = "true"
    Region      = local.Region
  }
}


resource "aws_security_group" "my-rds-security-group" {
  name   = "rds_security_group"
  vpc_id = aws_vpc.vpc.id
  tags = {
    Name        = "rds_security_group"
    Purpose     = "Intro to Resource Blocks Lab"
    Environment = var.environment
    team        = local.team
    application = local.application
    Terraform   = "true"
    Region      = local.Region
  }
}

resource "aws_security_group_rule" "allow_rds_sg" {
  type                     = "ingress"
  from_port                = 0
  to_port                  = 0
  protocol                 = "All"
  security_group_id        = aws_security_group.my-rds-security-group.id
  source_security_group_id = aws_security_group.my-elasticbeanstalk-security-group.id
}

resource "aws_security_group_rule" "allow_rds_sg_http" {
  type              = "ingress"
  from_port         = 5432
  to_port           = 5432
  protocol          = "tcp"
  prefix_list_ids   = ["pl-60b85b09"]
  security_group_id = aws_security_group.my-rds-security-group.id
}

resource "aws_security_group_rule" "allow_rds_sg_http_egress" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "All"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.my-rds-security-group.id
}


resource "aws_security_group" "my-elasticbeanstalk-security-group" {
  name   = "beanstalk_security_group"
  vpc_id = aws_vpc.vpc.id
  tags = {
    Name        = "beanstalk_security_group"
    Purpose     = "Intro to Resource Blocks Lab"
    Environment = var.environment
    team        = local.team
    application = local.application
    Terraform   = "true"
    Region      = local.Region
  }
}

resource "aws_security_group_rule" "allow_beanstalk_sg" {
  type                     = "ingress"
  from_port                = 0
  to_port                  = 0
  protocol                 = "All"
  security_group_id        = aws_security_group.my-elasticbeanstalk-security-group.id
  source_security_group_id = aws_security_group.my-rds-security-group.id
}


resource "aws_security_group_rule" "allow_beanstalk_sg_egress" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "All"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.my-elasticbeanstalk-security-group.id
}


#Provisioner Demo and example
#TLS Private Key
resource "tls_private_key" "generated" {
  algorithm = "RSA"
}

# Using Local module to write to local system
resource "local_file" "private_key" {
  content  = tls_private_key.generated.private_key_pem
  filename = "MyAWSKey.pem"
}


resource "aws_key_pair" "generated" {
  key_name   = "MyAWSKey"
  public_key = tls_private_key.generated.public_key_openssh

  lifecycle {
    ignore_changes = [key_name]
  }
}



resource "aws_instance" "web_server" {
  ami                         = "ami-051f8a213df8bc089"
  instance_type               = "t2.micro"
  subnet_id                   = aws_subnet.public_subnets["public_subnet_1"].id
  security_groups             = [aws_security_group.my-new-security-group.id]
  associate_public_ip_address = true
  key_name                    = aws_key_pair.generated.key_name
  provisioner "local-exec" {
    command = "chmod 600 ${local_file.private_key.filename}"
  }
  user_data = <<-EOF
                                        #!bin/bash
                                        sudo yum -y update
                                        sudo yum -y install java-1.8.0
                                        sudo wget https://archive.apache.org/dist/kafka/2.2.1/kafka_2.12-2.2.1.tgz
                                        sudo tar -xzf kafka_2.12-2.2.1.tgz
                                        echo "Java and kafka installed"
                                    EOF

  lifecycle {
    ignore_changes = [security_groups]
  }

  tags = {
    Name        = "MSKClient"
    Purpose     = "Intro to Resource Blocks Lab"
    Environment = var.environment
    team        = local.team
    application = local.application
    Terraform   = "true"
    Region      = local.Region
  }

}

#aws_s3_bucket_object
resource "aws_s3_object" "upload-script-files" {
  for_each = fileset("Glue/", "*")
  bucket   = aws_s3_bucket.my-new-S3-bucket.id
  key      = "Script/${each.value}"
  source   = "Glue/${each.value}"
  #etag = filemd5("myfiles/${each.value}")
}

resource "aws_s3_object" "upload-library-files" {
  for_each = fileset("Library/", "*")
  bucket   = aws_s3_bucket.my-new-S3-bucket.id
  key      = "Library/${each.value}"
  source   = "Library/${each.value}"
  #etag = filemd5("myfiles/${each.value}")
}

resource "aws_s3_object" "upload-config-files" {
  for_each = fileset("Config/", "*")
  bucket   = aws_s3_bucket.my-new-S3-bucket.id
  key      = "Config/${each.value}"
  source   = "Config/${each.value}"
}

resource "aws_s3_object" "upload-ran-template-file" {
  bucket = aws_s3_bucket.my-new-S3-bucket.id
  key    = "ran_gnodeb_template.xml"
  source = "ran_gnodeb_template.xml"
}

resource "aws_s3_object" "zip_file" {
  bucket = aws_s3_bucket.my-new-S3-bucket.id
  key    = "xmltodict.zip"
  source = "xmltodict.zip" #Replace with the path to your .zip file
}

resource "aws_iam_policy" "s3_access" {
  name   = "tf-s3-access"
  policy = <<-EOF
  {"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["s3:*","s3-object-lambda:*"],"Resource":"*"}]}
  EOF

}


resource "aws_iam_policy" "vpc_access" {
  name   = "tf-vpc-access"
  policy = <<-EOF
  {"Version":"2012-10-17","Statement":[{"Sid":"AmazonVPCFullAccess","Effect":"Allow","Action":["ec2:AcceptVpcPeeringConnection","ec2:AcceptVpcEndpointConnections","ec2:AllocateAddress","ec2:AssignIpv6Addresses","ec2:AssignPrivateIpAddresses","ec2:AssociateAddress","ec2:AssociateDhcpOptions","ec2:AssociateRouteTable","ec2:AssociateSubnetCidrBlock","ec2:AssociateVpcCidrBlock","ec2:AttachClassicLinkVpc","ec2:AttachInternetGateway","ec2:AttachNetworkInterface","ec2:AttachVpnGateway","ec2:AuthorizeSecurityGroupEgress","ec2:AuthorizeSecurityGroupIngress","ec2:CreateCarrierGateway","ec2:CreateCustomerGateway","ec2:CreateDefaultSubnet","ec2:CreateDefaultVpc","ec2:CreateDhcpOptions","ec2:CreateEgressOnlyInternetGateway","ec2:CreateFlowLogs","ec2:CreateInternetGateway","ec2:CreateLocalGatewayRouteTableVpcAssociation","ec2:CreateNatGateway","ec2:CreateNetworkAcl","ec2:CreateNetworkAclEntry","ec2:CreateNetworkInterface","ec2:CreateNetworkInterfacePermission","ec2:CreateRoute","ec2:CreateRouteTable","ec2:CreateSecurityGroup","ec2:CreateSubnet","ec2:CreateTags","ec2:CreateVpc","ec2:CreateVpcEndpoint","ec2:CreateVpcEndpointConnectionNotification","ec2:CreateVpcEndpointServiceConfiguration","ec2:CreateVpcPeeringConnection","ec2:CreateVpnConnection","ec2:CreateVpnConnectionRoute","ec2:CreateVpnGateway","ec2:DeleteCarrierGateway","ec2:DeleteCustomerGateway","ec2:DeleteDhcpOptions","ec2:DeleteEgressOnlyInternetGateway","ec2:DeleteFlowLogs","ec2:DeleteInternetGateway","ec2:DeleteLocalGatewayRouteTableVpcAssociation","ec2:DeleteNatGateway","ec2:DeleteNetworkAcl","ec2:DeleteNetworkAclEntry","ec2:DeleteNetworkInterface","ec2:DeleteNetworkInterfacePermission","ec2:DeleteRoute","ec2:DeleteRouteTable","ec2:DeleteSecurityGroup","ec2:DeleteSubnet","ec2:DeleteTags","ec2:DeleteVpc","ec2:DeleteVpcEndpoints","ec2:DeleteVpcEndpointConnectionNotifications","ec2:DeleteVpcEndpointServiceConfigurations","ec2:DeleteVpcPeeringConnection","ec2:DeleteVpnConnection","ec2:DeleteVpnConnectionRoute","ec2:DeleteVpnGateway","ec2:DescribeAccountAttributes","ec2:DescribeAddresses","ec2:DescribeAvailabilityZones","ec2:DescribeCarrierGateways","ec2:DescribeClassicLinkInstances","ec2:DescribeCustomerGateways","ec2:DescribeDhcpOptions","ec2:DescribeEgressOnlyInternetGateways","ec2:DescribeFlowLogs","ec2:DescribeInstances","ec2:DescribeInternetGateways","ec2:DescribeIpv6Pools","ec2:DescribeLocalGatewayRouteTables","ec2:DescribeLocalGatewayRouteTableVpcAssociations","ec2:DescribeKeyPairs","ec2:DescribeMovingAddresses","ec2:DescribeNatGateways","ec2:DescribeNetworkAcls","ec2:DescribeNetworkInterfaceAttribute","ec2:DescribeNetworkInterfacePermissions","ec2:DescribeNetworkInterfaces","ec2:DescribePrefixLists","ec2:DescribeRouteTables","ec2:DescribeSecurityGroupReferences","ec2:DescribeSecurityGroupRules","ec2:DescribeSecurityGroups","ec2:DescribeStaleSecurityGroups","ec2:DescribeSubnets","ec2:DescribeTags","ec2:DescribeVpcAttribute","ec2:DescribeVpcClassicLink","ec2:DescribeVpcClassicLinkDnsSupport","ec2:DescribeVpcEndpointConnectionNotifications","ec2:DescribeVpcEndpointConnections","ec2:DescribeVpcEndpoints","ec2:DescribeVpcEndpointServiceConfigurations","ec2:DescribeVpcEndpointServicePermissions","ec2:DescribeVpcEndpointServices","ec2:DescribeVpcPeeringConnections","ec2:DescribeVpcs","ec2:DescribeVpnConnections","ec2:DescribeVpnGateways","ec2:DetachClassicLinkVpc","ec2:DetachInternetGateway","ec2:DetachNetworkInterface","ec2:DetachVpnGateway","ec2:DisableVgwRoutePropagation","ec2:DisableVpcClassicLink","ec2:DisableVpcClassicLinkDnsSupport","ec2:DisassociateAddress","ec2:DisassociateRouteTable","ec2:DisassociateSubnetCidrBlock","ec2:DisassociateVpcCidrBlock","ec2:EnableVgwRoutePropagation","ec2:EnableVpcClassicLink","ec2:EnableVpcClassicLinkDnsSupport","ec2:GetSecurityGroupsForVpc","ec2:ModifyNetworkInterfaceAttribute","ec2:ModifySecurityGroupRules","ec2:ModifySubnetAttribute","ec2:ModifyVpcAttribute","ec2:ModifyVpcEndpoint","ec2:ModifyVpcEndpointConnectionNotification","ec2:ModifyVpcEndpointServiceConfiguration","ec2:ModifyVpcEndpointServicePermissions","ec2:ModifyVpcPeeringConnectionOptions","ec2:ModifyVpcTenancy","ec2:MoveAddressToVpc","ec2:RejectVpcEndpointConnections","ec2:RejectVpcPeeringConnection","ec2:ReleaseAddress","ec2:ReplaceNetworkAclAssociation","ec2:ReplaceNetworkAclEntry","ec2:ReplaceRoute","ec2:ReplaceRouteTableAssociation","ec2:ResetNetworkInterfaceAttribute","ec2:RestoreAddressToClassic","ec2:RevokeSecurityGroupEgress","ec2:RevokeSecurityGroupIngress","ec2:UnassignIpv6Addresses","ec2:UnassignPrivateIpAddresses","ec2:UpdateSecurityGroupRuleDescriptionsEgress","ec2:UpdateSecurityGroupRuleDescriptionsIngress"],"Resource":"*"}]}
  EOF
}


resource "aws_iam_policy" "glue_access" {
  name   = "tf-glue-access"
  policy = <<-EOF
  {"Version":"2012-10-17","Statement":[{"Action":["glue:*"],"Resource":["*"],"Effect":"Allow"},{"Action":["glue:GetDatabase"],"Resource":["*"],"Effect":"Allow"}]}
  EOF
}

resource "aws_iam_policy" "glue_service_role" {
  name   = "tf-glue-service-role"
  policy = <<-EOF
  {"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["glue:*","s3:GetBucketLocation","s3:ListBucket","s3:ListAllMyBuckets","s3:GetBucketAcl","ec2:DescribeVpcEndpoints","ec2:DescribeRouteTables","ec2:CreateNetworkInterface","ec2:DeleteNetworkInterface","ec2:DescribeNetworkInterfaces","ec2:DescribeSecurityGroups","ec2:DescribeSubnets","ec2:DescribeVpcAttribute","iam:ListRolePolicies","iam:GetRole","iam:GetRolePolicy","cloudwatch:PutMetricData"],"Resource":["*"]},{"Effect":"Allow","Action":["s3:CreateBucket"],"Resource":["arn:aws:s3:::aws-glue-*"]},{"Effect":"Allow","Action":["s3:GetObject","s3:PutObject","s3:DeleteObject"],"Resource":["arn:aws:s3:::aws-glue-*/*","arn:aws:s3:::*/*aws-glue-*/*"]},{"Effect":"Allow","Action":["s3:GetObject"],"Resource":["arn:aws:s3:::crawler-public*","arn:aws:s3:::aws-glue-*"]},{"Effect":"Allow","Action":["logs:CreateLogGroup","logs:CreateLogStream","logs:PutLogEvents"],"Resource":["arn:aws:logs:*:*:*:/aws-glue/*"]},{"Effect":"Allow","Action":["ec2:CreateTags","ec2:DeleteTags"],"Condition":{"ForAllValues:StringEquals":{"aws:TagKeys":["aws-glue-service-resource"]}},"Resource":["arn:aws:ec2:*:*:network-interface/*","arn:aws:ec2:*:*:security-group/*","arn:aws:ec2:*:*:instance/*"]}]}
  EOF
}


resource "aws_iam_policy" "kinesis_access" {
  name   = "tf-glue-kinesis-access"
  policy = <<-EOF
  {"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"kinesis:*","Resource":"*"}]}
  EOF
}

resource "aws_iam_policy" "secret_manger" {
  name   = "tf-lambda-secret-manager"
  policy = <<-EOF
  {"Version":"2012-10-17","Statement":[{"Sid":"VisualEditor0","Effect":"Allow","Action":["secretsmanager:GetRandomPassword","secretsmanager:ListSecrets","secretsmanager:BatchGetSecretValue"],"Resource":"*"},{"Sid":"VisualEditor1","Effect":"Allow","Action":"secretsmanager:*","Resource":"arn:aws:secretsmanager:*:${data.aws_caller_identity.current.account_id}:secret:*"}]}
  EOF
}

resource "aws_iam_policy" "lambda_basic_exec_opensearch" {
  name   = "tf-lambda-basic-execution-opensearch"
  policy = <<-EOF
  {"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"logs:CreateLogGroup","Resource":"arn:aws:logs:us-east-1:${data.aws_caller_identity.current.account_id}:*"},{"Effect":"Allow","Action":["logs:CreateLogStream","logs:PutLogEvents"],"Resource":["arn:aws:logs:us-east-1:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${local.lambda_opensearch}:*"]}]}
  EOF
}

resource "aws_iam_policy" "lambda_basic_exec_rule_engine" {
  name   = "tf-lambda-basic-execution-rule-engine"
  policy = <<-EOF
  {"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"logs:CreateLogGroup","Resource":"arn:aws:logs:us-east-1:${data.aws_caller_identity.current.account_id}:*"},{"Effect":"Allow","Action":["logs:CreateLogStream","logs:PutLogEvents"],"Resource":["arn:aws:logs:us-east-1:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${local.lambda_rule_engine}:*"]}]}
  EOF
}

resource "aws_iam_policy" "lambda_basic_exec_sf_trigger" {
  name   = "tf-lambda-basic-execution-sf-trigger"
  policy = <<-EOF
  {"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"logs:CreateLogGroup","Resource":"arn:aws:logs:us-east-1:${data.aws_caller_identity.current.account_id}:*"},{"Effect":"Allow","Action":["logs:CreateLogStream","logs:PutLogEvents"],"Resource":["arn:aws:logs:us-east-1:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${local.lambda_sf_trigger}:*"]}]}
  EOF
}

resource "aws_iam_policy" "lambda_invoke" {
  name   = "tf-lambda-invoke"
  policy = <<-EOF
  {"Version":"2012-10-17","Statement":[{"Sid":"Stmt1464440182000","Effect":"Allow","Action":["lambda:InvokeAsync","lambda:InvokeFunction"],"Resource":["*"]}]}
  EOF
}

resource "aws_iam_policy" "tf-lambda_vpc_access_exec_policy" {

  name   = "tf_lambda_vpc_access_exec_policy"
  policy = <<-EOF
  {"Version":"2012-10-17","Statement":[{"Sid":"AWSLambdaVPCAccessExecutionPermissions","Effect":"Allow","Action":["logs:CreateLogGroup","logs:CreateLogStream","logs:PutLogEvents","ec2:CreateNetworkInterface","ec2:DescribeNetworkInterfaces","ec2:DescribeSubnets","ec2:DeleteNetworkInterface","ec2:AssignPrivateIpAddresses","ec2:UnassignPrivateIpAddresses"],"Resource":"*"}]}
  EOF

}

resource "aws_iam_policy" "tf-lambda_exec_policy" {

  name   = "tf_lambda_exec_policy"
  policy = <<-EOF
  {"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["logs:*"],"Resource":"arn:aws:logs:*:*:*"},{"Effect":"Allow","Action":["s3:GetObject","s3:PutObject"],"Resource":"arn:aws:s3:::*"}]}
  EOF

}






resource "aws_iam_policy" "stepfunction_invoke" {
  name   = "tf-sf-invoke"
  policy = <<-EOF
  {"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"states:*","Resource":"*"}]}
  EOF
}




resource "aws_iam_role" "zeta-iam-role" {
  name = "zeta-iam-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = ["glue.amazonaws.com", "lambda.amazonaws.com", "ec2.amazonaws.com"]
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role" "zeta-iam-role-beanstalk" {
  name = "zeta-iam-role-beanstalk"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = ["ec2.amazonaws.com"]
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role" "sf-iam-role" {
  name = "zeta-iam-role-sf"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = ["states.amazonaws.com", "lambda.amazonaws.com"]
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}




resource "aws_iam_role_policy_attachment" "role-policy-attachment" {
  for_each = toset([
    "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/${aws_iam_policy.s3_access.name}",
    "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/${aws_iam_policy.vpc_access.name}",
    "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/${aws_iam_policy.glue_access.name}",
    "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/${aws_iam_policy.glue_service_role.name}",
    "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/${aws_iam_policy.kinesis_access.name}",
    "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/${aws_iam_policy.secret_manger.name}",
    "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/${aws_iam_policy.lambda_invoke.name}",
    "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/${aws_iam_policy.tf-lambda_vpc_access_exec_policy.name}",
    "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/${aws_iam_policy.tf-lambda_exec_policy.name}"
  ])
  role       = aws_iam_role.zeta-iam-role.name
  policy_arn = each.value

}

resource "aws_iam_role_policy_attachment" "role-policy-attachment-beanstalk" {
  for_each = toset([
    "arn:aws:iam::aws:policy/AWSElasticBeanstalkMulticontainerDocker",
    "arn:aws:iam::aws:policy/AWSElasticBeanstalkWebTier",
    "arn:aws:iam::aws:policy/AWSElasticBeanstalkWorkerTier"
  ])
  role       = aws_iam_role.zeta-iam-role-beanstalk.name
  policy_arn = each.value

}

resource "aws_iam_role_policy_attachment" "role-policy-attachment-stepfunction" {
  for_each = toset([
    "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/${aws_iam_policy.lambda_basic_exec_opensearch.name}",
    "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/${aws_iam_policy.vpc_access.name}",
    "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/${aws_iam_policy.lambda_basic_exec_rule_engine.name}",
    "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/${aws_iam_policy.lambda_basic_exec_sf_trigger.name}",
    "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/${aws_iam_policy.lambda_invoke.name}",
    "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/${aws_iam_policy.stepfunction_invoke.name}"
  ])
  role       = aws_iam_role.sf-iam-role.name
  policy_arn = each.value

}

# Creating a AWS secret for database master account (Masteraccoundb)

resource "aws_secretsmanager_secret" "secretmasterDB" {
  name                    = "Masteraccoundb-${random_id.randomness.hex}-new"
  recovery_window_in_days = 14
  tags = {
    Name        = "rds-${random_id.randomness.hex}"
    Purpose     = "Intro to Resource Blocks Lab"
    Environment = var.environment
    team        = local.team
    application = local.application
    Terraform   = "true"
    Region      = local.Region
  }

}

# Creating a AWS secret versions for database master account (Masteraccoundb)

resource "aws_secretsmanager_secret_version" "secret" {
  secret_id = aws_secretsmanager_secret.secretmasterDB.id
  secret_string = jsonencode({
    username = "zetaadmin",
    password = "Qwe${random_password.password.result}"
  })
}

output "secret_arn" {
  value = aws_secretsmanager_secret.secretmasterDB.arn

}


data "aws_secretsmanager_secret" "secrets_arn" {
  arn = aws_secretsmanager_secret.secretmasterDB.arn

}

data "aws_secretsmanager_secret_version" "current" {
  secret_id = data.aws_secretsmanager_secret.secrets_arn.id
}


#secret for opensearch
resource "aws_secretsmanager_secret" "secretmasteropensearchDB" {
  name                    = "Opensearch-${random_id.randomness.hex}-new"
  recovery_window_in_days = 14
  tags = {
    Name        = "Opensearch-${random_id.randomness.hex}"
    Purpose     = "Intro to Resource Blocks Lab"
    Environment = var.environment
    team        = local.team
    application = local.application
    Terraform   = "true"
    Region      = local.Region
  }

}

# Creating a AWS secret versions for database master account (Masteraccoundb)

resource "aws_secretsmanager_secret_version" "secret-opensearch" {
  secret_id = aws_secretsmanager_secret.secretmasteropensearchDB.id
  secret_string = jsonencode({
    username = "zetaadmin",
    password = "${random_password.password.result}@r"
  })
}

output "secret_arnopensearch" {
  value = aws_secretsmanager_secret.secretmasteropensearchDB.arn

}


data "aws_secretsmanager_secret" "secrets_arnopensearch" {
  arn = aws_secretsmanager_secret.secretmasteropensearchDB.arn

}

data "aws_secretsmanager_secret_version" "current-opensearch" {
  secret_id = data.aws_secretsmanager_secret.secrets_arnopensearch.id
}

resource "aws_db_subnet_group" "rds-subnet-group" {
  name       = "rds-subnet-group"
  subnet_ids = [aws_subnet.public_subnets["public_subnet_1"].id, aws_subnet.public_subnets["public_subnet_2"].id, aws_subnet.public_subnets["public_subnet_3"].id]

  tags = {
    Name = "Education"
  }
}

resource "aws_db_instance" "zeta-rds-postgres" {
  depends_on             = [aws_secretsmanager_secret_version.secret]
  identifier             = "zeta-rds-postgres"
  instance_class         = "db.t3.micro"
  allocated_storage      = 30
  engine                 = "postgres"
  engine_version         = "14.10"
  username               = jsondecode(data.aws_secretsmanager_secret_version.current.secret_string)["username"]
  password               = jsondecode(data.aws_secretsmanager_secret_version.current.secret_string)["password"]
  db_subnet_group_name   = aws_db_subnet_group.rds-subnet-group.name
  vpc_security_group_ids = [aws_security_group.my-rds-security-group.id]
  #parameter_group_name   = aws_db_parameter_group.education.name
  publicly_accessible = true
  skip_final_snapshot = true
}


resource "aws_iam_instance_profile" "ec2-instance-profile" {
  name = "ec2-instance-profile-new-version"
  role = aws_iam_role.zeta-iam-role-beanstalk.name

}

resource "aws_elastic_beanstalk_application" "zeta-app" {
  name        = "zeta-beanstalk-app-new-version"
  description = "Beanstalk application for zeta"
}

resource "aws_elastic_beanstalk_application_version" "v1" {
  name        = "version-1"
  application = aws_elastic_beanstalk_application.zeta-app.name
  description = "application version created by terraform"
  bucket      = aws_s3_bucket.my-new-S3-bucket.id
  key         = aws_s3_object.zip_file.id
}



#MSK
resource "aws_kms_key" "kafka_kms_key" {
  description = "Key for Apache Kafka"
}

resource "aws_msk_configuration" "kafka_config" {
  kafka_versions = ["2.8.1"]
  #name              = "${var.global_prefix}-config-${random_id.randomness.hex}"
  name              = "${var.global_prefix}-config"
  server_properties = <<EOF
                        auto.create.topics.enable = true
                        delete.topic.enable = true
EOF
}

resource "aws_cloudwatch_log_group" "kafka_log_group" {
  name = "msk_broker_logs"
  tags = {
    Name        = "zeta-kafka-cluster-log"
    Purpose     = "Intro to Resource Blocks Lab"
    Environment = var.environment
    team        = local.team
    application = local.application
    Terraform   = "true"
    Region      = local.Region
  }
}

resource "aws_msk_cluster" "kafka" {
  cluster_name           = var.global_prefix
  kafka_version          = "2.8.1"
  number_of_broker_nodes = 2
  broker_node_group_info {
    instance_type = "kafka.m5.large"
    storage_info {
      ebs_storage_info {
        volume_size = 80
      }
    }
    #client_subnets  = [aws_subnet.public_subnets["public_subnet_1"].id, aws_subnet.public_subnets["public_subnet_2"].id, aws_subnet.public_subnets["public_subnet_3"].id]
    client_subnets  = [aws_subnet.public_subnets["public_subnet_1"].id, aws_subnet.public_subnets["public_subnet_2"].id]
    security_groups = [aws_security_group.my-new-security-group.id]
  }
  encryption_info {
    encryption_in_transit {
      client_broker = "PLAINTEXT"
    }
    encryption_at_rest_kms_key_arn = aws_kms_key.kafka_kms_key.arn
  }
  configuration_info {
    arn      = aws_msk_configuration.kafka_config.arn
    revision = aws_msk_configuration.kafka_config.latest_revision
  }
  logging_info {
    broker_logs {
      cloudwatch_logs {
        enabled   = true
        log_group = aws_cloudwatch_log_group.kafka_log_group.name
      }
    }
  }
  tags = {
    Name        = var.global_prefix
    Purpose     = "Intro to Resource Blocks Lab"
    Environment = var.environment
    team        = local.team
    application = local.application
    Terraform   = "true"
    Region      = local.Region
  }
}


resource "aws_glue_connection" "MSKCONN" {
  connection_type = "KAFKA"

  connection_properties = {
    KAFKA_BOOTSTRAP_SERVERS = aws_msk_cluster.kafka.bootstrap_brokers
    KAFKA_SSL_ENABLED       = false
  }
  name = "MSK-Glue-Kafka-Connection"

  physical_connection_requirements {
    availability_zone      = ["${var.aws_region}a", "${var.aws_region}b", "${var.aws_region}c"][0]
    security_group_id_list = [aws_security_group.my-new-security-group.id]
    subnet_id              = aws_subnet.public_subnets["public_subnet_1"].id
  }

  tags = {
    Name        = "MSK-Glue-Kafka-Connection"
    Purpose     = "Intro to Resource Blocks Lab"
    Environment = var.environment
    team        = local.team
    application = local.application
    Terraform   = "true"
    Region      = local.Region
  }

}

resource "aws_lambda_layer_version" "lambda_layer_creation" {
  layer_name          = "requestmodulelayer"
  filename            = "${path.module}/Modules/python_requests_layer.zip"
  compatible_runtimes = ["python3.8"]

}


data "archive_file" "zip_ran_push_to_open_search" {
  type        = "zip"
  source_dir  = "${path.module}/Lambda/"
  output_path = "${path.module}/Lambda/ran_push_to_open_search.zip"
}

data "archive_file" "zip_ran_rule_engine_consumer" {
  type        = "zip"
  source_dir  = "${path.module}/Lambda/"
  output_path = "${path.module}/Lambda/ran_rule_engine_consumer.zip"
}


data "archive_file" "zip_ran_step_function_trigger" {
  type        = "zip"
  source_dir  = "${path.module}/Lambda/"
  output_path = "${path.module}/Lambda/ran_step_function_trigger.zip"
}


# Create a lambda function
# In terraform ${path.module} is the current directory.
resource "aws_lambda_function" "lambda_ran_push_to_open_search" {
  depends_on    = [aws_lambda_layer_version.lambda_layer_creation, data.archive_file.zip_ran_push_to_open_search]
  filename      = "${path.module}/Lambda/ran_push_to_open_search.zip"
  function_name = local.lambda_opensearch
  role          = aws_iam_role.zeta-iam-role.arn
  handler       = "ran_push_to_open_search.lambda_handler"
  runtime       = "python3.11"
  timeout       = 120
  vpc_config {
    subnet_ids         = [aws_subnet.private_subnets["private_subnet_1"].id]
    security_group_ids = [aws_security_group.my-new-security-group.id]
  }
  layers = [aws_lambda_layer_version.lambda_layer_creation.arn]
  tags = {
    Name        = local.lambda_opensearch
    Purpose     = "Intro to Resource Blocks Lab"
    Environment = var.environment
    team        = local.team
    application = local.application
    Terraform   = "true"
    Region      = local.Region
  }
}


resource "aws_lambda_function" "lambda_ran_rule_engine_consumer" {
  depends_on    = [aws_lambda_layer_version.lambda_layer_creation, data.archive_file.zip_ran_rule_engine_consumer]
  filename      = "${path.module}/Lambda/ran_rule_engine_consumer.zip"
  function_name = local.lambda_rule_engine
  role          = aws_iam_role.sf-iam-role.arn
  handler       = "ran_rule_engine_consumer.lambda_handler"
  runtime       = "python3.11"
  timeout       = 120
  vpc_config {
    subnet_ids         = [aws_subnet.private_subnets["private_subnet_1"].id]
    security_group_ids = [aws_security_group.my-new-security-group.id]
  }
  layers = [aws_lambda_layer_version.lambda_layer_creation.arn]
  tags = {
    Name        = local.lambda_rule_engine
    Purpose     = "Intro to Resource Blocks Lab"
    Environment = var.environment
    team        = local.team
    application = local.application
    Terraform   = "true"
    Region      = local.Region
  }
}



resource "aws_lambda_function" "lambda_ran_step_function_trigger" {
  depends_on    = [aws_lambda_layer_version.lambda_layer_creation, data.archive_file.zip_ran_step_function_trigger]
  filename      = "${path.module}/Lambda/ran_step_function_trigger.zip"
  function_name = local.lambda_sf_trigger
  role          = aws_iam_role.sf-iam-role.arn
  handler       = "ran_step_function_trigger.lambda_handler"
  runtime       = "python3.11"
  timeout       = 120
  vpc_config {
    subnet_ids         = [aws_subnet.private_subnets["private_subnet_1"].id]
    security_group_ids = [aws_security_group.my-new-security-group.id]
  }
  layers = [aws_lambda_layer_version.lambda_layer_creation.arn]
  tags = {
    Name        = local.lambda_sf_trigger
    Purpose     = "Intro to Resource Blocks Lab"
    Environment = var.environment
    team        = local.team
    application = local.application
    Terraform   = "true"
    Region      = local.Region
  }
}

resource "aws_kinesis_stream" "kinesis-stream" {
  name             = "zeta-kinesis-stream"
  retention_period = 48

  shard_level_metrics = [
    "IncomingBytes",
    "OutgoingBytes",
  ]

  stream_mode_details {
    stream_mode = "ON_DEMAND"
  }

  tags = {
    Name        = "zeta-kinesis-stream"
    Purpose     = "Intro to Resource Blocks Lab"
    Environment = var.environment
    team        = local.team
    application = local.application
    Terraform   = "true"
    Region      = local.Region
  }
}




data "aws_iam_policy_document" "opensearch_access_policy" {
  #checkov:skip=CKV_AWS_283:Solution does not require to be that restrictive
  statement {
    effect    = "Allow"
    actions   = ["es:*"]
    resources = ["arn:aws:es:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:domain/${local.domain_name}/*"]
    principals {
      type        = "AWS"
      identifiers = ["*"]
    }
  }
}



resource "aws_opensearch_domain" "ran-opensearch" {
  domain_name     = local.domain_name
  engine_version  = "OpenSearch_2.7"
  access_policies = data.aws_iam_policy_document.opensearch_access_policy.json

  vpc_options {
    security_group_ids = [aws_security_group.my-new-security-group.id]
    subnet_ids         = [aws_subnet.public_subnets["public_subnet_1"].id, aws_subnet.public_subnets["public_subnet_2"].id]

  }

  cluster_config {
    instance_type            = "m5.large.search"
    instance_count           = "6"
    warm_enabled             = "false"
    dedicated_master_enabled = true
    zone_awareness_enabled   = true
    cold_storage_options {
      enabled = false
    }
    dedicated_master_count = 3
  }

  advanced_security_options {
    enabled                        = true
    anonymous_auth_enabled         = false
    internal_user_database_enabled = true
    master_user_options {
      master_user_name     = jsondecode(data.aws_secretsmanager_secret_version.current-opensearch.secret_string)["username"]
      master_user_password = jsondecode(data.aws_secretsmanager_secret_version.current-opensearch.secret_string)["password"]
    }
  }

  encrypt_at_rest {
    enabled = true
  }

  domain_endpoint_options {
    enforce_https       = true
    tls_security_policy = "Policy-Min-TLS-1-2-2019-07"
  }

  node_to_node_encryption {
    enabled = "true"

  }

  ebs_options {
    ebs_enabled = true
    volume_size = 50
    volume_type = "gp3"
  }

  tags = {
    Name        = local.domain_name
    Purpose     = "Intro to Resource Blocks Lab"
    Environment = var.environment
    team        = local.team
    application = local.application
    Terraform   = "true"
    Region      = local.Region
  }

}

resource "aws_glue_job" "ran" {
  name              = "ran-data-generator"
  role_arn          = aws_iam_role.zeta-iam-role.arn
  glue_version      = "3.0"
  worker_type       = "G.1X"
  number_of_workers = "4"

  command {
    script_location = "s3://${aws_s3_bucket.my-new-S3-bucket.id}/Script/ran_data_generator.py"
    python_version  = "3"

  }
  connections = [aws_glue_connection.MSKCONN.name]
  default_arguments = {
    "--job-language"                     = "python"
    "--ENV"                              = "env"
    "--spark-event-logs-path"            = "s3://${aws_s3_bucket.my-new-S3-bucket.id}/spark_event_log/"
    "--enable-continuous-cloudwatch-log" = "true"
    "--enable-spark-ui"                  = "true"
    "--ANOMALY_END_DATE"                 = "2023-08-03"
    "--ANOMALY_END_TIME"                 = "7"
    "--ANOMALY_FLAG"                     = "on"
    "--ANOMALY_START_DATE"               = "2023-08-03"
    "--ANOMALY_START_TIME"               = "1"
    "--DAYS_OF_WEEK"                     = "[1,2,3,4,5,6,7]"
    "--END_DATE"                         = "2023-08-03"
    "--NUMBER_OF_ANOMALIES"              = "7"
    "--START_DATE"                       = "2023-08-02"
    "--TARGET_BUCKET"                    = aws_s3_bucket.my-new-S3-bucket.id
    "--TARGET_PLATFORM"                  = "msk"
    "--MSK_BROKER"                       = aws_msk_cluster.kafka.bootstrap_brokers
    "--TOPIC_NAME"                       = "RAN_GENERATOR_PRODUCER_NEW_1"
    "--S3_PREFIX"                        = "raw_data/"
    "--KINSESIS_STREAM"                  = aws_kinesis_stream.kinesis-stream.name
    "--FREQUENCY"                        = "1"
    "--REFERENCE_FILE"                   = "ran_gnodeb_template.xml"
    "--extra-py-files"                   = "s3://${aws_s3_bucket.my-new-S3-bucket.id}/Library/kafka.zip,s3://${aws_s3_bucket.my-new-S3-bucket.id}/Library/xmltodict.zip"

  }
  tags = {
    Name        = "ran-data-generator"
    Purpose     = "Intro to Resource Blocks Lab"
    Environment = var.environment
    team        = local.team
    application = local.application
    Terraform   = "true"
    Region      = local.Region
  }
}

resource "aws_glue_job" "ran-parser" {
  name              = "ran-streaming-parser"
  role_arn          = aws_iam_role.zeta-iam-role.arn
  glue_version      = "3.0"
  worker_type       = "G.2X"
  number_of_workers = "4"

  command {
    script_location = "s3://${aws_s3_bucket.my-new-S3-bucket.id}/Script/ran_streaming_parser.py"
    python_version  = "3"

  }
  connections = [aws_glue_connection.MSKCONN.name]
  default_arguments = {
    "--job-language"                     = "python"
    "--ENV"                              = "env"
    "--spark-event-logs-path"            = "s3://${aws_s3_bucket.my-new-S3-bucket.id}/spark_event_log/"
    "--enable-continuous-cloudwatch-log" = "true"
    "--enable-spark-ui"                  = "true"
    "--TARGET_BUCKET"                    = aws_s3_bucket.my-new-S3-bucket.id
    "--MSK_BROKER"                       = aws_msk_cluster.kafka.bootstrap_brokers
    "--FREQUENCY"                        = "1"
    "--CONSUMER_TOPIC_NAME"              = "RAN_GENERATOR_PRODUCER_NEW_1"
    "--PRODUCER_TOPIC_NAME"              = "RAN_PARSED_DATA_PRODUCER_2"
    "--TARGET_S3_PREFIX"                 = "kafka_results/"
    "--CHECKPOINT_DIR"                   = "checkpointDir/"
    "--extra-py-files"                   = "s3://${aws_s3_bucket.my-new-S3-bucket.id}/Library/kafka.zip,s3://${aws_s3_bucket.my-new-S3-bucket.id}/Library/xmltodict.zip"

  }
  tags = {
    Name        = "ran-streaming-parser"
    Purpose     = "Intro to Resource Blocks Lab"
    Environment = var.environment
    team        = local.team
    application = local.application
    Terraform   = "true"
    Region      = local.Region
  }
}

resource "aws_elastic_beanstalk_environment" "zeta-env" {
  name                = "zeta-beanstalk-env-new-version"
  application         = aws_elastic_beanstalk_application_version.v1.application
  version_label       = aws_elastic_beanstalk_application_version.v1.name
  solution_stack_name = "64bit Amazon Linux 2023 v5.1.5 running Tomcat 10 Corretto 17" #Change to Tomcat 8.5 with Corretto 8 running on 64bit Amazon Linux 2/4.3.4
  #solution_stack_name = "64bit Amazon Linux 2 v4.4.1 running Tomcat 8.5 Corretto 8" #Change to Tomcat 8.5 with Corretto 8 running on 64bit Amazon Linux 2/4.3.4
  cname_prefix = "zeta-dev-elastic-beanstalk"
  setting {
    namespace = "aws:autoscaling:launchconfiguration"
    name      = "IamInstanceProfile"
    value     = aws_iam_instance_profile.ec2-instance-profile.name
  }
  setting {
    namespace = "aws:autoscaling:launchconfiguration"
    name      = "SecurityGroups"
    value     = aws_security_group.my-elasticbeanstalk-security-group.id
  }

  setting {
    namespace = "aws:ec2:vpc"
    name      = "AssociatePublicIpAddress"
    value     = "True"
  }
  setting {
    namespace = "aws:elasticbeanstalk:environment:process:default"
    name      = "MatcherHTTPCode"
    value     = "200"
  }
  setting {
    namespace = "aws:autoscaling:launchconfiguration"
    name      = "InstanceType"
    value     = "t2.micro"
  }
  setting {
    namespace = "aws:autoscaling:launchconfiguration"
    name      = "ImageId"
    value     = "ami-051f8a213df8bc089" # Replace with your desired AMI ID
  }
  setting {
    namespace = "aws:ec2:vpc"
    name      = "VpcId"
    value     = aws_vpc.vpc.id
  }
  /*setting {
    namespace = "aws:ec2:instance"
    name      = "BeanStalkInstance"
    value     = aws_vpc.vpc.id
  }*/

  setting {
    namespace = "aws:ec2:vpc"
    name      = "Subnets"
    value     = aws_subnet.public_subnets["public_subnet_1"].id
  }
  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "SERVER_PORT"
    value     = "5000"
  }
  setting {
    namespace = "aws:elasticbeanstalk:environment"
    name      = "LoadBalancerType"
    value     = "classic"
  }
  setting {
    namespace = "aws:elasticbeanstalk:environment"
    name      = "EnvironmentType"
    value     = "SingleInstance"
  }
  setting {
    namespace = "aws:elasticbeanstalk:healthreporting:system"
    name      = "SystemType"
    value     = "basic"
  }

  #database connection
  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "DATABASE_HOST"
    value     = aws_db_instance.zeta-rds-postgres.endpoint
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "DATABASE_USERNAME"
    value     = aws_db_instance.zeta-rds-postgres.username
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "DATABASE_PASSWORD"
    value     = aws_db_instance.zeta-rds-postgres.password
  }

}

resource "aws_sfn_state_machine" "ran-sf-1" {
  name     = "ran-step-function"
  role_arn = aws_iam_role.sf-iam-role.arn

  definition = <<EOF
{
  "Comment": "A description of my state machine",
  "StartAt": "InvokeRestAPI",
  "States": {
    "InvokeRestAPI": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "OutputPath": "$.Payload",
      "Parameters": {
        "Payload.$": "$",
        "FunctionName": "${aws_lambda_function.lambda_ran_rule_engine_consumer.arn}"
      },
      "Retry": [
        {
          "ErrorEquals": [
            "Lambda.ServiceException",
            "Lambda.AWSLambdaException",
            "Lambda.SdkClientException",
            "Lambda.TooManyRequestsException"
          ],
          "IntervalSeconds": 2,
          "MaxAttempts": 6,
          "BackoffRate": 2
        }
      ],
      "Next": "write_to_es"
    },
    "write_to_es": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "OutputPath": "$.Payload",
      "Parameters": {
        "Payload.$": "$",
        "FunctionName": "${aws_lambda_function.lambda_ran_push_to_open_search.arn}"
      },
      "Retry": [
        {
          "ErrorEquals": [
            "Lambda.ServiceException",
            "Lambda.AWSLambdaException",
            "Lambda.SdkClientException",
            "Lambda.TooManyRequestsException"
          ],
          "IntervalSeconds": 2,
          "MaxAttempts": 6,
          "BackoffRate": 2
        }
      ],
      "End": true
    }
  }
}
EOF
}

resource "aws_glue_job" "ran-request-generator" {
  name              = "ran-request-generator"
  role_arn          = aws_iam_role.zeta-iam-role.arn
  glue_version      = "3.0"
  worker_type       = "G.2X"
  number_of_workers = "4"

  command {
    script_location = "s3://${aws_s3_bucket.my-new-S3-bucket.id}/Script/ran_request_generator.py"
    python_version  = "3"

  }
  connections = [aws_glue_connection.MSKCONN.name]
  default_arguments = {
    "--job-language"                     = "python"
    "--ENV"                              = "env"
    "--spark-event-logs-path"            = "s3://${aws_s3_bucket.my-new-S3-bucket.id}/spark_event_log/"
    "--enable-continuous-cloudwatch-log" = "true"
    "--enable-spark-ui"                  = "true"
    "--TARGET_BUCKET"                    = aws_s3_bucket.my-new-S3-bucket.id
    "--MSK_BROKER"                       = aws_msk_cluster.kafka.bootstrap_brokers
    "--CONSUMER_TOPIC_NAME"              = "RAN_PARSED_DATA_PRODUCER_2"
    "--AWS_SECRET_ID"                    = aws_secretsmanager_secret.secretmasteropensearchDB.name
    "--RULE_ENGINE_URL"                  = aws_elastic_beanstalk_environment.zeta-env.cname
    "--OPENSEARCH_ENDPOINT"              = aws_opensearch_domain.ran-opensearch.endpoint
    "--INDEX_NAME"                       = "ran_document_index"
    "--OFFSET"                           = "earliest"
    "--BATCH_SIZE"                       = "3"
    "--LAMBDA_FUNC_NAME"                 = local.lambda_sf_trigger
    "--STEPFUNCTION_ARN"                 = aws_sfn_state_machine.ran-sf-1.arn
    "--PLATFORM"                         = "ran"
    "--extra-py-files"                   = "s3://${aws_s3_bucket.my-new-S3-bucket.id}/Library/kafka.zip,s3://${aws_s3_bucket.my-new-S3-bucket.id}/Library/xmltodict.zip"

  }
  tags = {
    Name        = "ran-request-generator"
    Purpose     = "Intro to Resource Blocks Lab"
    Environment = var.environment
    team        = local.team
    application = local.application
    Terraform   = "true"
    Region      = local.Region
  }
}
