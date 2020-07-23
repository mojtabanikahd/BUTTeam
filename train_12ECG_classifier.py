
import os
import glob
import numpy as np
import glob
import numpy as np
from torch import optim
from torch.utils import data




from config import Config
from log import Log

# from dataset import Dataset

import net

from get_data_info import enumerate_labels,sub_dataset_labels_sum





def train_12ECG_classifier(input_directory, output_directory):
    
    device = Config.DEVICE
    
    

   
    file_list = glob.glob(input_directory + r"\**\*.mat", recursive=True)
    num_files = len(file_list)
    
    # Train-Test split
    np.random.seed(666)
    split_ratio_ind = int(np.floor(Config.SPLIT_RATIO[0] / (Config.SPLIT_RATIO[0] + Config.SPLIT_RATIO[1]) * num_files))
    permuted_idx = np.random.permutation(num_files)
    train_ind = permuted_idx[:split_ratio_ind]
    valid_ind = permuted_idx[split_ratio_ind:]
    partition = {"train": [file_list[file_idx] for file_idx in train_ind],
        "valid": [file_list[file_idx] for file_idx in valid_ind]}
    
    
    #### run once
    # binary_labels=enumerate_labels(file_list, dict(zip(Config.HASH_TABLE['snomeds'],Config.HASH_TABLE['abb'])))
    
    lbl_counts=sub_dataset_labels_sum(partition["train"])    
    num_of_sigs=len(partition["train"])

    # w_positive=(num_of_sigs-lbl_counts)/lbl_counts
    # w_negative=np.ones_like(w_positive)

    w_positive=num_of_sigs/lbl_counts
    w_negative=num_of_sigs/(num_of_sigs-lbl_counts)
    
    w_positive_tensor=torch.from_numpy(w_positive.astype(np.float32)).to(device)
    w_negative_tensor=torch.from_numpy(w_negative.astype(np.float32)).to(device)
    
    
    # Train dataset generator
    training_set = Dataset( partition["train"],transform=Config.TRANSFORM_DATA_TRAIN,encode=Config.TRANSFORM_LBL)
    training_generator = data.DataLoader(training_set,batch_size=Config.BATCH_TRAIN,num_workers=Config.TRAIN_NUM_WORKERS,shuffle=True,drop_last=True,collate_fn=Dataset.collate_fn )
    
    
    validation_set = Dataset(partition["valid"],transform=Config.TRANSFORM_DATA_VALID,encode=Config.TRANSFORM_LBL)
    validation_generator = data.DataLoader(validation_set,batch_size=Config.BATCH_VALID,num_workers=Config.VALID_NUM_WORKERS,shuffle=True,drop_last=True,collate_fn=Dataset.collate_fn )
    
    
    model = net.Net_addition_grow(levels=Config.LEVELS,lvl1_size=Config.LVL1_SIZE,input_size=Config.INPUT_SIZE,output_size=Config.OUTPUT_SIZE,convs_in_layer=Config.CONVS_IN_LAYERS,init_conv=Config.INIT_CONV,filter_size=Config.FILTER_SIZE)
    
    
    model=model.to(device)

    ## create optimizer and learning rate scheduler to change learnng rate after 
    optimizer = optim.Adam(model.parameters(),lr =Config.INIT_LR ,betas= (0.9, 0.999),eps=1e-8,weight_decay=1e-8)
    scheduler= optim.lr_scheduler.StepLR(optimizer, Config.STEP_SIZE, gamma=Config.GAMMA, last_epoch=-1)
    
    log=Log(['loss','challange_metric'])
    
    for epoch in range(Config.max_epochs):
        
        #change model to training mode
        model.train()
        for pad_seqs,lens,lbls in training_generator:
            
            ## send data to graphic card
            pad_seqs,lens,lbls = pad_seqs.to(device),lens.to(device),lbls.to(device)

            ## aply model
            res=model(pad_seqs,lens)
            
            ## calculate loss
            loss=Config.LOSS_FCN(res,lbls,w_positive_tensor,w_negative_tensor)

            ## update model 
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()


            loss=loss.detach().cpu().numpy()
            res=res.detach().cpu().numpy()
            lbls=lbls.detach().cpu().numpy()

            
            challange_metric=compute_challenge_metric_custom(res,lbls)

            ## save results
            log.append_train([loss,challange_metric])
      



        ## validation mode - "disable" batch norm 
        model.eval() 
        for pad_seqs,lens,lbls in validation_generator:

            pad_seqs,lens,lbls = pad_seqs.to(device),lens.to(device),lbls.to(device)

            res=model(pad_seqs,lens)
            
            loss=Config.LOSS_FCN(res,lbls,w_positive_tensor,w_negative_tensor)

            loss=loss.detach().cpu().numpy()
            res=res.detach().cpu().numpy()
            lbls=lbls.detach().cpu().numpy()

            
            challange_metric=compute_challenge_metric_custom(res,lbls)

            ## save results
            log.append_test([loss,challange_metric])
        
        
        ## save optimal treshhold to model 
                
        lr=get_lr(optimizer)
        
        info= str(epoch) + '_' + str(lr) + '_train_'  + str(log.trainig_log['challange_metric'][-1]) + '_valid_' +str(log.train_log['challange_metric'][-1])) 
        print(info)
        
        model_name=Config.model_save_dir+ os.sep + Config.model_note + info  + '.pkl'
        log.save_log_model_name(model_name)
        model.save_log(log)
        model.save_config(Config)
        torch.save(model,model_name)
            
        log.plot()
        
        scheduler.step()
    
    
    
    
    
    
    
    
    
    
    


if __name__ == '__main__':
    # Parse arguments.
    input_directory = '../data'
    output_directory = '42'

    if not os.path.isdir(output_directory):
        os.mkdir(output_directory)

    print('Running training code...')

    train_12ECG_classifier(input_directory, output_directory)

    print('Done.')


