/**
 *  Alexander Haggart, 4/11/18
 *
 *  BeeF interpreter implementation
 *
 *  supply instruction plaintext file as a command-line argument
 */

#include <stdio.h>
#include <time.h>

#include "BeeFVirtualMachine.h"
#include "BVMStack.h"
#include "Preprocessor.h"

void print_usage(){
  printf("usage: roast path_to_beef_assembly\n");
}

int main(int argc, char** argv){
  if(argc < 2){
    print_usage();
    return 1;
  }
  BVM* vm = create_bvm(10);
  FILE* insns = fopen(argv[1],"r");
  FILE* prog = insns;
  PP_INFO_T* info = ppreprocessor(prog);
  pp_dump_info(info);

  printf("Starting Virtual Machine...\n* * * * *\n");
  int running = 1;
  unsigned int step_counter = 0;
  int status = 0;
  char insn;
  time_t start = clock();
  while(1){
    insn = info->i_cache[vm->pc];
    if((status=process(vm,insn))>0){
      printf("Error: Interpreter exited with code: %d\n",status);
      break;
    }else if(status == BVM_REQ_BRANCH){ //vm requests pc branch
      vm->pc = info->br_cache[vm->pc-1]; //find matching brace
    }
    if(vm->pc >= info->i_count){
      break;
    }
    step_counter++;
  }

  const char* fmt = "Stopping Virtual Machine...\nCompleted %u steps in %fs\n";
  printf(fmt,step_counter,(float)(clock() - start)/CLOCKS_PER_SEC);
  dump_bvm(vm);

  return status;
}
