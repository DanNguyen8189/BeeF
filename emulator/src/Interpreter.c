/**
 *  Alexander Haggart, 4/11/18
 *
 *  BeeF interpreter implementation
 *
 *  supply instruction plaintext file as a command-line argument
 */

#include <stdio.h>
#include "Grinder.h"
#include "GStack.h"

void print_usage(){
  printf("usage: grind path_to_beef_assembly\n");
}

unsigned int preprocessor(FILE* src,char* icache,unsigned int* branch_shortcuts){
  char insn;
  unsigned int insn_c = 0;
  while((insn=fgetc(src))!=EOF){
    if(is_instruction(insn)){
      icache[insn_c++] = insn;
    }
  }
  GStack* branch_stack = gcreate_stack(16,sizeof(unsigned int));
  unsigned int pc,branch_to;
  for(pc = 0; pc < insn_c; pc++){
    if((insn=icache[pc]) == '['){
      gspush(branch_stack,(GSTACK_DATA_PTR_T)&pc);
    } else if(insn == ']'){
      if(!(branch_to = *(unsigned int*)gspop(branch_stack))){
        printf("Error: Unmatched conditional branches at %u.\n",pc);
        return 1;
      }
      branch_shortcuts[branch_to] = pc+1;
      branch_shortcuts[pc] = branch_to+1;
    } else{
      branch_shortcuts[pc] = 0;
    }
  }

  return insn_c;
}

int main(int argc, char** argv){
  if(argc < 2){
    print_usage();
    return 1;
  }
  Grinder* vm = create_grinder(3);
  FILE* insns = fopen(argv[1],"r");
  FILE* prog = insns;

  //load the whole program
  fseek(prog,0,SEEK_END);
  long len = ftell(prog);
  char instruction_cache[len];
  char* icache = instruction_cache;
  fseek(prog,0,SEEK_SET);
 
  //program preprocessor -- not an efficient implementation
  unsigned int branch_shortcuts[len];
  unsigned int insn_c = preprocessor(prog,icache,branch_shortcuts);
  printf("Loaded program %s (%d instructions).\n",argv[1],insn_c);

  // gsdump(branch_stack);

  // printf("Branch Shortcuts:\n");
  // for(pc = 0;pc < insn_c;pc++){
  //   printf("\tshortcut @ %u: %u\n",pc,branch_shortcuts[pc]);
  // }

  int running = 1;
  unsigned int step_counter = 0;
  int status = 0;
  char insn;
  while(1){
    insn = instruction_cache[vm->pc];
    if((status=process(vm,insn))>0){
      printf("Error: Interpreter exited with code: %d\n",status);
      break;
    }else if(status == GRINDREQ_BRANCH){
      vm->pc = branch_shortcuts[vm->pc-1]; //find matching brace
    }
    if(vm->pc >= len){
      break;
    }
    step_counter++;
  }
  printf("Done interpretting!\nCompleted in %u steps\n",step_counter);
  dump_grinder(vm);

  return status;
}