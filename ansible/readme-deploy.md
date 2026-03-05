# 🚀 Deployment Guide — SIH Models Monorepo

This guide walks you through deploying all 3 AI models to AWS EC2 using a **single command**. The Ansible playbook handles everything automatically: SSH keys, Terraform infrastructure, model deployment, and Nginx routing.

---

## What Gets Deployed

| Model | EC2 Type | Disk | Port | Domain |
|---|---|---|---|---|
| **Vision** (Image Classification) | t2.medium | 20 GB | 8002 | `vision-ani.adityahota.online` |
| **Voice** (RAG Chatbot + Voice) | t2.large | 50 GB | 8001 | `voice-ani.adityahota.online` |
| **Abuse** (Toxicity Detection) | t2.small | 8 GB | 8000 | `toxic-ani.adityahota.online` |

---

## Prerequisites

Before running the deployment, make sure you have these installed on your **local machine**:

### 1. Install Required Tools

```bash
# Ansible
sudo apt install ansible -y

# Terraform
# Follow: https://developer.hashicorp.com/terraform/install

# AWS CLI
# Follow: https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html

# Ansible collections (needed by the playbook)
ansible-galaxy collection install community.general community.crypto
```

### 2. Configure AWS CLI

```bash
aws configure
```

Enter your:
- **AWS Access Key ID**
- **AWS Secret Access Key**
- **Default region**: `ap-south-1`
- **Default output format**: `json`

You need permissions for: EC2, VPC, Security Groups, Key Pairs.

### 3. Verify AWS is Working

```bash
aws sts get-caller-identity
```

You should see your account ID and user ARN. If this errors out, fix your credentials first.

---

## How to Deploy (One Command!)

```bash
cd ansible/
ansible-playbook deploy.yml
```

That's it. Go grab a coffee ☕ — it'll take ~10-15 minutes.

---

## What the Playbook Does (Step by Step)

Here's what happens behind the scenes when you run the command:

### Step 1: SSH Key Generation
- Creates `ansible/.key/` folder
- Generates a 4096-bit RSA key pair (`id_rsa` + `id_rsa.pub`)
- This key is used to SSH into the EC2 instances

### Step 2: Terraform Init + Validate + Apply
- Initializes Terraform (`terraform init`)
- Validates the config (`terraform validate`)
- Creates 3 EC2 instances on AWS
- Prints the public IPs of all 3 servers

### Step 3: SSH Verification
- Waits for all 3 EC2s to boot up
- Pings each one over SSH to confirm connectivity
- If you see `✅ SSH OK` for all 3, you're good!

### Step 4: Common Setup (on all 3 EC2s)
- Updates apt packages
- Installs: `nginx`, `git`, `python3`, `pip`, `venv`
- Installs `ffmpeg` on the Voice EC2 (needed for audio processing)
- Clones the repo from GitHub

### Step 5: Environment Variables
- Writes `.env` files with API keys (HuggingFace, Groq, LangChain) to each model's directory
- The Abuse model also gets `GROQ_MODEL=llama-3.3-70b-versatile`

### Step 6-8: Model Deployment (Vision, Voice, Abuse)
For each model:
1. Creates a Python virtual environment
2. Installs `requirements.txt`
3. Creates a systemd service (so it auto-restarts)
4. Configures Nginx for name-based routing
5. Starts the model API

---

## After Deployment

### Check if Models are Running

SSH into any EC2 (the IPs are printed during deployment):

```bash
ssh -i ansible/.key/id_rsa ubuntu@<EC2_IP>
```

Then check the service status:

```bash
# On Vision EC2
sudo systemctl status vision-service

# On Voice EC2
sudo systemctl status voice-service

# On Abuse EC2
sudo systemctl status abuse-service
```

### Check Nginx

```bash
sudo nginx -t          # Should say "syntax is ok"
sudo systemctl status nginx
```

### Test the APIs

```bash
# From your local machine — replace <IP> with actual EC2 IP

# Vision model
curl http://<VISION_IP>:8002/

# Voice model
curl http://<VOICE_IP>:8001/

# Abuse model
curl http://<ABUSE_IP>:8000/
```

Or if DNS is configured:

```bash
curl http://vision-ani.adityahota.online/
curl http://voice-ani.adityahota.online/
curl http://toxic-ani.adityahota.online/
```

---

## Tear Down (Destroy Everything)

To destroy all 3 EC2 instances:

```bash
cd ansible/terraform/
terraform destroy
```

Type `yes` when prompted. This will terminate all servers and delete the security group.

---

## Troubleshooting

### "Permission denied (publickey)" when SSH-ing
- Make sure the `.key/id_rsa` file exists: `ls -la ansible/.key/`
- If not, run the playbook again — it will regenerate the key

### Terraform errors about credentials
- Run `aws sts get-caller-identity` — if it fails, re-run `aws configure`
- Make sure your IAM user has EC2 permissions

### Model service not starting
SSH into the EC2 and check logs:
```bash
sudo journalctl -u vision-service -f    # or voice-service / abuse-service
```

### Nginx not routing
```bash
sudo nginx -t                                  # Check for config errors
ls -la /etc/nginx/sites-enabled/               # Should show your site configs
sudo systemctl restart nginx
```

---

## Project Structure

```
ansible/
├── .key/                    # SSH keys (auto-generated, git-ignored)
│   ├── id_rsa               # Private key (NEVER commit this)
│   └── id_rsa.pub           # Public key (uploaded to AWS)
├── terraform/
│   ├── main.tf              # 3 EC2 instances + security group
│   └── outputs.tf           # Exports public IPs
├── templates/
│   ├── vision_nginx.conf.j2 # Nginx config for vision model
│   ├── voice_nginx.conf.j2  # Nginx config for voice model
│   └── toxic_nginx.conf.j2  # Nginx config for abuse model
├── ansible.cfg              # Ansible settings
└── deploy.yml               # THE playbook — run this!
```

---

## ⚡ Quick Start: Full Deployment Command

To start the full end-to-end deployment of all infrastructure and models, simply run:

```bash
cd ansible/
ansible-playbook deploy.yml
```

### VIEW LOGS
```bash
# SSH into them first
ssh -i ansible/.key/id_rsa ubuntu@<EC2_IP>

sudo journalctl -u vision-service -f    # or voice-service / abuse-service
```

### VIEW NGINX
```bash
sudo systemctl status nginx
```