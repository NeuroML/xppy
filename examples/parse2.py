import sys
from pprint import pprint

def _split_if_then_else(expr):
    print('Splitting: %s'%expr)
    condition = expr[2:].split('then')[0]
    value_true = expr[2:].split('then')[1].split('else')[0]
    value_false = expr[2:].split('then')[1].split('else')[1]

    return {'condition':condition,"value_true":value_true,"value_false":value_false}

def _add_cond_deriv_var():
    pass

INBUILT = {'pi':3.14159265359}

def parse_script(file_path):
    data = {
        "comments": [],
        "parameters": dict(INBUILT),
        "functions": {},
        "derived_variables": {},
        "conditional_derived_variables": {},
        "time_derivatives": {},
        "initial_values": {},
        "settings": {},
        "unhandled": []
    }

    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip()
            if not line:
                continue

            # Handle comments
            if line.startswith("#"):
                c = line[1:].strip()
                if len(c)>0:
                    data["comments"].append(c)

            # Handle parameter declarations
            elif line.startswith(('number', 'p', 'par')):
                params = line.replace('number ', '').replace('par ', '').replace('p ', '')  # Skip the first word ('number', 'p', or 'par')
                for pp1 in params.split(','):
                    for pp2 in pp1.split(' '):
                        if len(pp2)>0:
                            key, value = pp2.split('=')
                            data["parameters"][key.strip()] = float(value.strip())

            # Handle init declarations
            elif line.startswith(('init')):
                inits = line[5:]
                for pp in inits.split(','):
                    if len(pp)>0:
                        key, value = pp.split('=')
                        data["initial_values"][key.strip()] = float(value.strip())

            # Handle function and initial value declarations
            elif '=' in line and not line.startswith("@"):
                key, value = line.split('=', 1)
                if "'" in key:
                    # Initial value
                    var_name = key.split("'")[0].strip()
                    data["time_derivatives"][var_name] = value.strip()
                elif '[0]' in key or '(0)' in key:
                    # Initial value
                    var_name = key.split('[')[0].split('(')[0].strip()
                    data["initial_values"][var_name] = float(value.strip())
                elif '(' in key:
                    # Function definition
                    func_name = key.split('(')[0].strip()
                    func_args = key.split('(')[1].split(')')[0].strip().split(',')
                    data["functions"][func_name] = {}
                    data["functions"][func_name]['arguments'] = func_args
                    data["functions"][func_name]['value'] = value.strip()
                else:
                    # "Normal" variable...
                    expr = value.strip()
                    if 'if' in expr and 'else' in expr:
                        
                        data["conditional_derived_variables"][key.strip()] = _split_if_then_else(expr)
                    else:
                        data["derived_variables"][key.strip()] = expr

            # Handle done
            elif line == 'done':
                pass

            # Handle settings
            elif line.startswith("@"):
                settings = line[1:].strip()
                for sss in settings.split(' '):
                    for ss in sss.split(','):
                        if len(ss)>0:
                            key, value = ss.split('=')
                            data["settings"][key.strip().lower()] = value.strip()

                

            else:
                data["unhandled"].append(line)

    return data

def substitute_functions(expr, functions):

    import re

    for func_name, func_def in functions.items():
        # print('  - Function %s, replacing %s in <%s>'%(func_name, func_def,expr))
        # Find all occurrences of the function in the expression
        pattern = f"{func_name}\(([^)]+)\)"
        matches = re.findall(pattern, expr)

        for match in matches:
            args_in_expr = match.split(',')
            if len(args_in_expr) != len(func_def['arguments']):
                raise ValueError(f"Incorrect number of arguments for function {func_name}")

            # Map the arguments in the expression to the function definition
            substitution = func_def['value']
            for def_arg, expr_arg in zip(func_def['arguments'], args_in_expr):

                substitution = substitution.replace(def_arg, expr_arg.strip())
                # print('    - replacing <%s> by <%s> - <%s>'%(def_arg, expr_arg.strip(), substitution))

            # Replace the function call with the substitution
            expr = expr.replace(f"{func_name}({match})", substitution)

        # print('  - Expr now: <%s>'%(expr))
    return expr

def to_xpp(data, new_xpp_filename):

    xpp_ode = ''

    xpp_ode+='\n# Parameters\n'
    for k,v in data["parameters"].items():
        if not k in INBUILT.keys():
            xpp_ode += f'{k} = {v}\n'

    xpp_ode+='\n# Functions\n'
    for k,v in data["functions"].items():
        xpp_ode += f'{k}('
        for a in v['arguments']: xpp_ode += '%s,'%a
        xpp_ode=xpp_ode[:-1]
        xpp_ode += ') = %s\n'%v['value']

    xpp_ode+='\n# Time derivatives\n'
    for k,v in data["time_derivatives"].items():
        xpp_ode += f"{k}' = {v}\n"

    xpp_ode+='\n# Derived variables\n'
    for k,v in data["derived_variables"].items():
        xpp_ode += f"{k} = {v}\n"

    xpp_ode+='\n# Initial values\n'
    for k,v in data["initial_values"].items():
        xpp_ode += f"init {k} = {v}\n"

    xpp_ode+='\n# Settings\n'
    for k,v in data["settings"].items():
        xpp_ode += f"@ {k.upper()}={v}\n"
    
    xpp_ode+='\ndone\n'

    with open(new_xpp_filename, 'w') as f:
        f.write(xpp_ode)

    print('Written %s'%new_xpp_filename)



def to_lems(data, lems_model_id, lems_model_file):

    import lems.api as lems

    model = lems.Model()

    ct = lems.ComponentType("XPP_model")

    model.add(ct)
    
    comp = lems.Component("%s_0"%ct.name, ct.name)
    model.add(comp)
        
        
    ct.add(lems.Constant('MSEC', '1ms', "time"))

    for k,v in data["parameters"].items():
        ct.add(lems.Parameter(k, "none"))
        comp.set_parameter(k,v)

    os = lems.OnStart()
    ct.dynamics.add(os)

    for k,v in data["initial_values"].items():
        os.add(lems.StateAssignment(k,str(v)))
    
    for k,v in data["derived_variables"].items():
        ct.add(lems.Exposure(k, "none"))

        dv_expr = substitute_functions(v, data["functions"])
        print(f"DV: <{v}> -> <{dv_expr}>")

        ct.dynamics.add(lems.DerivedVariable(name=k, exposure=k, dimension='none', value=dv_expr))
    
    for k,v in data["time_derivatives"].items():
        ct.add(lems.Exposure(k, "none"))
        ct.dynamics.add(lems.StateVariable(k, "none", k))

        td_expr = substitute_functions(v, data["functions"])
        print(f"TD: <{v}> -> <{td_expr}>")

        ct.dynamics.add(lems.TimeDerivative(k, '(%s)/MSEC'%td_expr))

    print('Saving LEMS model to: %s'%lems_model_file)
    model.export_to_file(lems_model_file)


    from pyneuroml.lems import LEMSSimulation

    duration = float(data['settings']['total']) if 'total' in data['settings'] else 1000
    dt = float(data['settings']['dtmin']) if 'dtmin' in data['settings'] else \
           (float(data['settings']['dt']) if 'dt' in data['settings'] else 0.025)
    
    ls = LEMSSimulation(lems_model_id, duration, dt, comp.id)

    ls.include_lems_file(lems_model_file)

    
    disp0 = "Exposures"

    ls.create_display(disp0, "Params", "-90", "50")

    from pyneuroml.utils.plot import get_next_hex_color
    for e in ct.exposures:
        ls.add_line_to_display(disp0, e.name, "%s"%(e.name), "1", get_next_hex_color())

    '''
    of0 = "Volts_file"
    ls.create_output_file(of0, "%s.v.dat" % lems_model_id)
    ls.add_column_to_output_file(of0, "v", "hhpop[0]/v")

    eof0 = "Events_file"
    ls.create_event_output_file(eof0, "%s.v.spikes" % lems_model_id, format="ID_TIME")

    ls.add_selection_to_event_output_file(eof0, "0", "hhpop[0]", "spike")'''

    ls.set_report_file("report.txt")

    print("Using information to generate LEMS: ")
    pprint(ls.lems_info)
    print("\nLEMS: ")
    print(ls.to_xml())

    ls.save_to_file()



if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <filename>")
        sys.exit(1)

    file_path = sys.argv[1]
    parsed_data = parse_script(file_path)
    pprint(parsed_data)

    lems_model_id = file_path.replace('.ode','').split('/')[-1]
    lems_model_file = file_path.replace('.ode','.model.xml')

    to_lems(parsed_data, lems_model_id, lems_model_file)
    to_xpp(parsed_data, file_path.replace('.ode','_2.ode'))