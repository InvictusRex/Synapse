"""
Synapse Setup Script for Windows
Run this once to set up the 'synapse' command
"""
import os
import sys
import subprocess

def main():
    print("\n" + "="*50)
    print("  SYNAPSE - Windows Setup")
    print("="*50 + "\n")
    
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Step 1: Install dependencies
    print("[1/3] Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", 
                              os.path.join(script_dir, "requirements.txt"), "-q"])
        print("      Done!\n")
    except subprocess.CalledProcessError:
        print("      Warning: Some dependencies may have failed to install\n")
    
    # Step 2: Create the batch file wrapper
    print("[2/3] Creating synapse.bat...")
    bat_content = f'@echo off\npython "{os.path.join(script_dir, "cli.py")}" %*\n'
    bat_path = os.path.join(script_dir, "synapse.bat")
    with open(bat_path, 'w') as f:
        f.write(bat_content)
    print("      Done!\n")
    
    # Step 3: Add to PowerShell profile
    print("[3/3] Setting up 'synapse' command...")
    
    # Get PowerShell profile path
    ps_profile_dir = os.path.join(os.environ.get('USERPROFILE', ''), 'Documents', 'WindowsPowerShell')
    ps_profile = os.path.join(ps_profile_dir, 'Microsoft.PowerShell_profile.ps1')
    
    # Create profile directory if it doesn't exist
    os.makedirs(ps_profile_dir, exist_ok=True)
    
    # Alias line to add
    alias_line = f'\n# Synapse CLI\nfunction synapse {{ python "{os.path.join(script_dir, "cli.py")}" @args }}\n'
    
    # Check if alias already exists
    existing_content = ""
    if os.path.exists(ps_profile):
        with open(ps_profile, 'r') as f:
            existing_content = f.read()
    
    if "function synapse" not in existing_content:
        with open(ps_profile, 'a') as f:
            f.write(alias_line)
        print("      Added 'synapse' command to PowerShell profile!\n")
    else:
        print("      'synapse' command already exists in profile\n")
    
    # Done
    print("="*50)
    print("  SETUP COMPLETE!")
    print("="*50)
    print(f"""
To use Synapse:

  Option 1: Open a NEW PowerShell window and type:
            synapse

  Option 2: From this folder, run:
            .\\synapse.bat
            
  Option 3: Run directly:
            python cli.py

Note: The API key is stored in .env file.
      You can change it there if needed.
""")

if __name__ == "__main__":
    main()
