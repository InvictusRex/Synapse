"""
Synapse Setup Script for Linux
Run this once to set up the 'synapse' command
"""
import os
import sys
import subprocess

def main():
    print("\n" + "="*50)
    print("  SYNAPSE - Linux Setup")
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
    
    # Step 2: Make shell script executable
    print("[2/3] Creating synapse command...")
    sh_path = os.path.join(script_dir, "synapse.sh")
    sh_content = f'''#!/bin/bash
python3 "{os.path.join(script_dir, "cli.py")}" "$@"
'''
    with open(sh_path, 'w') as f:
        f.write(sh_content)
    os.chmod(sh_path, 0o755)
    print("      Done!\n")
    
    # Step 3: Add alias to .bashrc
    print("[3/3] Setting up 'synapse' command...")
    
    home = os.path.expanduser('~')
    bashrc_path = os.path.join(home, '.bashrc')
    
    # Also check for .zshrc if it exists
    zshrc_path = os.path.join(home, '.zshrc')
    
    # Alias line to add
    alias_line = f'\n# Synapse CLI\nalias synapse=\'python3 "{os.path.join(script_dir, "cli.py")}"\'\n'
    
    profiles_updated = []
    
    # Update .bashrc
    if os.path.exists(bashrc_path):
        with open(bashrc_path, 'r') as f:
            existing_content = f.read()
        
        if "alias synapse" not in existing_content:
            with open(bashrc_path, 'a') as f:
                f.write(alias_line)
            profiles_updated.append(bashrc_path)
    
    # Update .zshrc if it exists
    if os.path.exists(zshrc_path):
        with open(zshrc_path, 'r') as f:
            existing_content = f.read()
        
        if "alias synapse" not in existing_content:
            with open(zshrc_path, 'a') as f:
                f.write(alias_line)
            profiles_updated.append(zshrc_path)
    
    if profiles_updated:
        print(f"      Added 'synapse' command to: {', '.join(profiles_updated)}\n")
    else:
        print("      'synapse' command already exists in profile(s)\n")
    
    # Done
    print("="*50)
    print("  SETUP COMPLETE!")
    print("="*50)
    print(f"""
To use Synapse:

  Option 1: Open a NEW terminal window and type:
            synapse

  Option 2: From this folder, run:
            ./synapse.sh
            
  Option 3: Run directly:
            python3 cli.py

  Option 4: Reload your profile now:
            source ~/.bashrc
            synapse

Note: The API key is stored in .env file.
      You can change it there if needed.
""")

if __name__ == "__main__":
    main()
