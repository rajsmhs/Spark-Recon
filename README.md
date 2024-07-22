"Maestro Unzipping job (Step 1) is not working because of gpg key unavailibility
Impact: Delay in delivery of LoanIQ modules End to End runs"	Subhasish Guha	16/07/24	Open	- Framework/ops team to response	Rowan Davies	Extreme	"Resolution: Framework team need to import gpg keys from on-premise and place it at an secure location.
Action Plan: Raised this with Rowan on July 18 and the team is unaware of on-prem location for these keys."	No target as the Famework team is unaware of how to resolve issue
"Maestro Parsed data generation (Step 2) not working as expecten.

Impact: Delay in delivery of LoanIQ modules End to End runs
"	Subhasish Guha	16/07/24	Open	Framework Team to respond	Rowan Davies	Medium	"Presently the the Maestro output is getting stored at hdfs location not on s3 and the archival data is stored at edge node's storage[Not even EBS]

Recommendation: There is no CICD process to deploy the code in S3. Discuss internally and establish a recommended process for CBA.

Action plan: Discussed with Rowan and he made some code changes but unable to deploy the code on cluster. Once Rowan installs CLI on his laptop the code can"	Framework/Ops team has not provided a completion date
"Autosys Scheduler is not onboarded which is resulting in manual execution of steps

Impact: Jobs cannot be run through scheduler and manual intervention is needed which is not ideal in long run. there are 25k jobs

Impact: Delay in delivery of LoanIQ modules End to End runs"	Subhasish Guha	16/07/24	Open	Scope and Schedule	Tushar/Niko	Extreme	"All the jobs are written as a part of wrapper shell scripts which are scheduled by Autosys services which is yet to onboard. Presently no Autosys + houston integrated instances have been onboarded.

Recommendation: None available in proposed architecture 

Action plan: AWS team to discuss how to lift & shift this autosys & houston schduler and "	Discuss with Niko on recommendations and make a technical decision
"Spark ETL sub modules test/deployment

Impact: Delay in delivery of LoanIQ modules End to End runs"	Subhasish Guha	16/07/24	Open	Framework team to response	Niko / Rowan Davies	Extreme	"Spakr ETL framework has sub modules i.e DIL, ENR, OLM etc. Only Spark DIL framework has been tested for day 0 day 1 jobs after making significant amount of changes at the YAML and spark-runner.sh

Recommendation: Test every pattern of jobs from Framework. Identify unique patterns to be tested.

Action plan: Follow the steps made in YAML and spark-runner.sh for DIL and implement the same for other modules "	Discuss with Niko on recommendations and make a technical decision how to implement this approach for 25k jobs
"Maestro unable to read from S3 storage. This means all the data need to reside in master node which is high risk for data loss when it goes down
Currently upto 12TB of edge node storage is used on-prem."	 	18/07/24	OPen	Design	Niko	Extreme	"Resolution opion 1: Change Framework code to read and write to S3 which ened to addressed by CBA framework SME. 
Resolution option 2: Leverage 12 TB EBS volume as-is with on-prem to avoid any cluster storage failure. However this is cost intensive and is not feasible option."	 
"Timeline risks about Migration Playbook
Impact : AWS is involved for the last 8 weeks and we are unable to achieve end to end runs for LoanIQ modules. It will impact during the scale phase"								 ![image](https://github.com/user-attachments/assets/5ff491ea-5dc3-4877-b85d-0b308f188b5f)
