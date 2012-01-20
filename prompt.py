#!/bin/env python
"""
prompt - multiline prompt
"""

# Simple embedded multiline python interpreter built around raw_input().
# Interrupts the control flow at any given location with 'exec prompt'
# and gives control to the user.
# Allways runs in the current scope and can even be started from the 
# pdb prompt in debugging mode. Tested with python, jython and stackless.
# Handy for simple debugging purposes.

#not mine. from:
#http://code.activestate.com/recipes/285214-prompt-simple-multiline-interactive-interpreter/

prompt = compile("""
try:
    _prompt
    _recursion = 1
except:
    _recursion = 0
if not _recursion:
    from traceback import print_exc as print_exc
    from traceback import extract_stack
    _prompt = {'print_exc':print_exc, 'inp':'','inp2':'','co':''}
    _a_es, _b_es, _c_es, _d_es = extract_stack()[-2]
    if _c_es == '?':
        _c_es = '__main__'
    else:
        _c_es += '()' 
    print '\\nprompt in %s at %s:%s  -  continue with CTRL-D' % (_c_es, _a_es, _b_es)
    del _a_es, _b_es, _c_es, _d_es, _recursion, extract_stack, print_exc
    while 1:
        try:
            _prompt['inp']=raw_input('>>> ')
            if not _prompt['inp']:
                continue
            if _prompt['inp'][-1] == chr(4): 
                break
            exec compile(_prompt['inp'],'<prompt>','single')
        except EOFError:
            print
            break
        except SyntaxError:
            while 1:
                _prompt['inp']+=chr(10)
                try:
                    _prompt['inp2']=raw_input('... ')
                    if _prompt['inp2']:
                        if _prompt['inp2'][-1] == chr(4): 
                            print
                            break
                        _prompt['inp']=_prompt['inp']+_prompt['inp2']
                    _prompt['co']=compile(_prompt['inp'],'<prompt>','exec')
                    if not _prompt['inp2']: 
                        exec _prompt['co']
                        break
                    continue
                except EOFError:
                    print
                    break
                except:
                    if _prompt['inp2']: 
                        continue
                    _prompt['print_exc']()
                    break
        except:
            _prompt['print_exc']()
    print '--- continue ----'
    # delete the prompts stuff at the end
    del _prompt
""", '<prompt>', 'exec')

# runs the testcase
if __name__=='__main__': 

    def my_func():
        exec prompt

    class prompt_test:
        def __init__(self):
            self.init = 'init'
        def test_method(self):
            self.dummy = 'dummy'
            # interrupt control flow inside a method
            exec prompt
    
    # 1: exec prompt inside a method
    prompt_test().test_method()
    
    # 2: exec prompt inside a function
    my_func()
    
    # 3: exec prompt inside the modules global scope
    exec prompt
