import driver_py
import evaluate_12ECG_score
import evaluate_12ECG_score_nan
import numpy as np
import shutil
import os

data_path='../Training_WFDB'
# data_path='../prvnich1000'

res_path='../res'

shutil.rmtree(res_path)


try:
    os.mkdir(res_path)
except:
    pass


         
driver_py.driver(data_path,res_path)


auroc,auprc,accuracy,f_measure,f_beta,g_beta = evaluate_12ECG_score_nan.evaluate_12ECG_score(data_path,res_path)

output_string = 'AUROC|AUPRC|Accuracy|F-measure|Fbeta-measure|Gbeta-measure\n{:.3f}|{:.3f}|{:.3f}|{:.3f}|{:.3f}|{:.3f}'.format(auroc,auprc,accuracy,f_measure,f_beta,g_beta)


print(output_string)
    
    
print(np.sqrt(f_beta*g_beta))