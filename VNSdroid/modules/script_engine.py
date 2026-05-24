import os
import re
from kivy.logger import Logger

class ScriptEngine:
    def __init__(self):
        self.script_lines = []
        self.current_line_idx = 0
        self.current_script_name = "main.scr"
       
        self.variables = {"selected": 0}
   
        self.labels = {}

    def load_script(self, path):
        self.current_script_name = os.path.basename(path)
        self.script_lines = []
        self.labels = {}
        self.current_line_idx = 0
        
        if not path or not os.path.exists(path):
            Logger.error(f"ScriptEngine: Script path does not exist: {path}")
            return False

        try:
            with open(path, 'r', encoding='utf-8') as f:
                raw_lines = f.readlines()
            
            idx = 0
            for line in raw_lines:
                cleaned = line.strip()
          
                if not cleaned or cleaned.startswith('#'):
                    continue
                
                self.script_lines.append(cleaned)
                
                parts = cleaned.split(' ', 1)
                cmd = parts[0].lower()
                if cmd == "label" and len(parts) > 1:
                    lbl_name = parts[1].strip()
                    self.labels[lbl_name] = idx
                idx += 1
                
            return True
        except Exception as e:
            Logger.error(f"ScriptEngine Error loading script {path}: {e}")
            return False

    def evaluate_expression(self, expr_str):
    
        expr_str = expr_str.strip()

        matches = re.findall(r'\{\$([^}]+)\}', expr_str)
        for var_name in matches:
            var_name_clean = var_name.strip()
            val = str(self.variables.get(var_name_clean, ""))
            expr_str = expr_str.replace(f"{{${var_name}}}", val)
        return expr_str

    def evaluate_condition(self, condition_str):
 
        if '==' in condition_str:
            var_part, val_part = condition_str.split('==', 1)
            var_name = var_part.strip()
            target_val = val_part.strip()
            
    
            actual_val = str(self.variables.get(var_name, "0"))
            return actual_val == target_val
            
        return False

    def handle_variable_assignment(self, args):
    
        if '=' in args:
            var_part, val_part = args.split('=', 1)
            var_name = var_part.strip()
            val_str = self.evaluate_expression(val_part.strip())
            
      
            try:
                if val_str.isdigit():
                    val = int(val_str)
                else:
                    val = float(val_str)
            except ValueError:
                val = val_str.strip('"')
                
            self.variables[var_name] = val
        else:
    
            parts = args.split()
            if len(parts) >= 2:
                var_name = parts[0].strip()
                val_str = self.evaluate_expression(parts[1].strip())
                self.variables[var_name] = val_str

    def get_next_command(self):
        if self.current_line_idx >= len(self.script_lines):
            return None, ""
            
        line = self.script_lines[self.current_line_idx]
        self.current_line_idx += 1
        
        parts = line.split(' ', 1)
        cmd = parts[0].lower()
        args = parts[1].strip() if len(parts) > 1 else ""

        if args and cmd not in ["text", "if"]:
            args = self.evaluate_expression(args)
            
        return cmd, args

    def local_goto(self, label_name):
     
        if label_name in self.labels:
            self.current_line_idx = self.labels[label_name]
            return True
        Logger.warning(f"ScriptEngine: Target label '{label_name}' not mapped in {self.current_script_name}")
        return False
