#include "Preprocessor.h"
#include "BeeFVirtualMachine.h"

PPD_RETURN_T ppd_console_out(SRC_LEN_T line,PPD_DATA_PTR_T data){
    printf("Line %ld: %s",line,data);
    return 0;
}

PPD_DATA_PTR_T ppd_make_console_out(char* dir){
    size_t len = (strlen(dir)+1)*sizeof(char); //include newline
    void* msg = malloc(len);
    return strcpy(msg,dir);
}

PP_DEBUG_T* pp_make_debug_data(BF_INSN_T* dir){
    //parse the directive
    if(dir[0] != PP_DELIM){//what are ya doin man
        return 0;
    }
    SRC_LEN_T idx = 0;
    while(dir[++idx] != PP_DELIM); //seek next delimiter
    dir[idx] = 0; //null terminate the ID
    PP_DEBUG_T* dest = (PP_DEBUG_T*)malloc(sizeof(PP_DEBUG_T));
    dest->type = atoi(dir+1);

    //type-specific parsing
    switch(dest->type){
        case PP_DIR_CONSOLE_OUT: //print to console 
        default: //default to printqing directive if we dont recognize it
            dest->data = ppd_make_console_out(dir+idx+1);
            // printf("%p: %s",dest,dest->data);
            dest->execute = &ppd_console_out;
            break;
    }

    return dest;
}

SRC_LEN_T pp_get_debug_info(FILE* src, PP_INFO_T* info){
    const int READ_BUFFER_SIZE = 256; //these dont need to be exposed
    const int DEBUG_DATA_SIZE  = 1;  //where to put

    char read_buffer[READ_BUFFER_SIZE];
    info->d_count = 0;
    int debug_array_size = DEBUG_DATA_SIZE;
    info->debug_data = PP_MK_DEBUG_BUF(DEBUG_DATA_SIZE);

    while(1){
        //directives must end with newline
        if(!fgets(read_buffer,READ_BUFFER_SIZE,src)){
            break;
        }
        if(read_buffer[0] == PP_DELIM){
            if(info->d_count == debug_array_size){
                PP_DEBUG_T** tmp = PP_MK_DEBUG_BUF(debug_array_size*2);
                memcpy(tmp,info->debug_data,debug_array_size*sizeof(PP_DEBUG_T*));
                free(info->debug_data);
                debug_array_size *= 2;
                info->debug_data = tmp;
            }
            info->debug_data[info->d_count] = pp_make_debug_data(read_buffer);
            info->d_count++;
            info->line_count++;
        } else {
            fseek(src,-strlen(read_buffer),SEEK_CUR);
            break;
        }
    }

    return ftell(src);
}

SRC_LEN_T pp_link_debug_info(FILE* src, SRC_LEN_T maxlen){
    BF_INSN_T byte;
    BF_INSN_T ref[maxlen];
    SRC_LEN_T reflen = 0;

    while((byte = fgetc(src))!=EOF){
        if(byte == PP_DELIM){
            break;
        } else if(reflen < maxlen){
            ref[reflen++] = byte;
        }
    }
    ref[reflen] = 0; //null terminate
    if(byte != PP_DELIM){
        printf("Error: Reached end of file expecting: %c\n",PP_DELIM);
        return -1;
    }

    return atoi(ref);
}

void pp_dump_info(PP_INFO_T* info){
    printf("Dumping Preprocessor Info:\n");
    printf(FMT_INDENT "Source Line Count: %ld\n",info->line_count);
    printf(FMT_INDENT "Total Instruction Count: %ld\n",info->i_count);
    printf(FMT_INDENT "Directives found: %ld\n",info->d_count);
    SRC_LEN_T i = 0;
    while(i<info->d_count){
        printf("%ld: %p\n",i,info->debug_data[i]);
        i++;
    }
    printf(FMT_INDENT "Raw Instruction Data: ");
    i = 0;
    while(i<info->i_count){
        printf("%c",info->i_cache[i++]);
    }
    printf("\n");
    printf(FMT_INDENT "Raw Ref Data: ");
    i = 0;
    SRC_LEN_T link;
    while(i<info->i_count){
        if((link=info->d_cache[(i++)*2]) != PPD_REF_INVALID){
            printf(" %ld(%ld) ",link,info->d_cache[i*2-1]);
        } else {
            printf("_");
        }
    }
    printf("\n");
    printf(FMT_INDENT "Raw Branch Data: ");
    i = 0;
    while(i<info->i_count){
        if((link=info->br_cache[i++]) != PP_NO_BRANCH){
            printf(" %ld ",link);
        } else {
            printf("_");
        }
    }
    printf("\n");
}

PP_INFO_T* ppreprocessor(FILE* src){
    PP_INFO_T* info = (PP_INFO_T*)malloc(sizeof(PP_INFO_T));

    SRC_LEN_T pos = 0;

    //parse the debugging headers, if any
    info->line_count = 1;
    pos = pp_get_debug_info(src,info);
    SRC_LEN_T maxlen = (SRC_LEN_T)log10(info->d_count)+1; //max valid ref size
    // printf("Reference max digit length: %ld\n",maxlen);

    //parse the remaining code, stripping out non-command chars
    fseek(src,0,SEEK_END);
    SRC_LEN_T srclen = ftell(src) - pos;
    fseek(src,pos,SEEK_SET);
    BF_INSN_T readbuffer[srclen]; //max possible size
    SRC_LEN_T refbuffer[srclen*2]; //max possible size
    SRC_LEN_T brbuffer[srclen];
    BVMS* br_stack = bvms_create_stack(16,sizeof(SRC_LEN_T));

    BF_INSN_T insn;
    SRC_LEN_T i_count = 0;
    SRC_LEN_T branch_to;
    while((insn = fgetc(src))!=EOF){
        if(is_instruction(insn)){
            readbuffer[i_count] = insn;
            refbuffer[i_count*2] = PPD_REF_INVALID;
            if(insn == '['){ //macro it?
                bvms_push(br_stack,(BVMS_DATA_PTR_T)&i_count);
            } else if(insn == ']'){
                if(!(branch_to = *(unsigned int*)bvms_pop(br_stack))){
                    printf("Error: Unmatched conditional branches %ld.\n",i_count);
                    printf("Preprocessor Abort\n");
                    break;
                }
                brbuffer[branch_to] = i_count+1;
                brbuffer[i_count] = branch_to+1;
            } else{
                brbuffer[i_count] = PP_NO_BRANCH;
            }
            i_count++;
        } else if(insn == PP_DELIM){
            if(i_count == 0){
                printf("Error: Unable to bind reference\n");
                pp_link_debug_info(src,maxlen); //consume the ref without link
                continue;
            }
            refbuffer[(i_count-1)*2]   = pp_link_debug_info(src,maxlen);
            refbuffer[(i_count-1)*2+1] = info->line_count;
        } else if(insn == '\n'){
            info->line_count++;
        }
    }

    printf("Found %ld instructions\n",i_count);

    //create the final buffers
    info->i_cache  = (BF_INSN_PTR_T)malloc(i_count*sizeof(BF_INSN_T));
    info->d_cache  = (SRC_LEN_T*)malloc(i_count*sizeof(SRC_LEN_T)*2);
    info->br_cache = (SRC_LEN_T*)malloc(i_count*sizeof(SRC_LEN_T));

    memcpy(info->i_cache, readbuffer,i_count*sizeof(BF_INSN_T));
    memcpy(info->d_cache, refbuffer, i_count*sizeof(SRC_LEN_T)*2);
    memcpy(info->br_cache,brbuffer,  i_count*sizeof(SRC_LEN_T));

    info->i_count = i_count;

    return info;
}