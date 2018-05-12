module top_level(
  input clk,
        reset,
  output logic done
);

logic Halt;
logic [7:0] PC;     //how big is our PC????
logic [7:0] PCIncremented;  //after incrementing PC
logic [7:0] PCSelected;   //PC after mux picks source
  
logic [8:0] Instruction;  //machine code
logic [7:0] alu_i;
logic [7:0] alu_result_o;
logic overflow_o;

logic [7:0] cacheptr,     //out from resgister file
            stackptr,
      headptr,
      registerptr;
logic [7:0] registerInputSelect; //no name register input data

logic [7:0] memDataOut;   //data memory read output
logic [7:0] memReadAddress;
logic [7:0] memWriteAddress;        //data memory write access location

InstROM #(.IW(16)) im1(
  .InstAddress (PC),
  .Instruction (Instruction)
);

single_reg programCounter(
  .clk    (clk  ),
  .regReadEnable  (1'b1 ),    //always reading
  .regWriteEnable (),     //???????????????????????
  .regWriteData (PCSelected),
  .regReadData  (PC    )
);

alu pc_alu(
  .alu_data_i (PC ),
  .op_i   (1'b0 ),    //always adding
  .alu_result_o (PCincremented),
  .overflow_o ()      //are we using overflow????????????
);

single_reg cache(
  .clk    (clk  ),
  .regReadEnable  (1'b1 ),    //always reading
  .regWriteEnable (),
  .regWriteData (alu_result_o),
  .regReadData  (cacheptr    )
);

single_reg stack(
  .clk    (clk  ),
  .regReadEnable  (1'b1 ),    //always reading
  .regWriteEnable (),
  .regWriteData (alu_result_o),
  .regReadData  (stackptr)
);

single_reg head(
  .clk    (clk  ),
  .regReadEnable  (1'b1 ),    //always reading
  .regWriteEnable (),
  .regWriteData (alu_result_o),
  .regReadData  (headptr)
);

single_reg no_name_register(
  .clk    (clk  ),
  .regReadEnable  (1'b1 ),    //always reading
  .regWriteEnable (),
  .regWriteData (registerInputSelect),
  .regReadData  (registerptr)
);

alu alu_main(
  .alu_data_i   (alu_i         ),
  .op_i   (Instruction[0]),
  .alu_result_o (alu_result_o  ),
  .overflow_o (     ) //are we using overflow???????????????????
);

data_mem dm1(
        .clk            (clk        ),        
        .memReadAddress (memReadAddress ),
  .memWriteAddress(memWriteAddress),
    .ReadMem        (1'b1       ),    // mem read always on   
    .WriteMem       (Instruction[7]), // write on or off
    .DataIn         (memDataIn  ),    //data to write   
    .DataOut        (memDataOut )     //read result
);

four_one_mux alu_mux( 
  .selector (Instruction[2:1]),
  .indata1  (registerptr ),
  .indata2  (headptr  ),
  .indata3  (stackptr ),
  .indata4  (cacheptr ),
  .outdata  (alu_i    )
);

four_one_mux pc_source_mux(
  .selector (),     //what picks the source??????????????????????????????
  .indata1  (PCIncremented  ),
  .indata2  (cacheptr     ),
  .indata3  (hold       ),  //where is this coming from
  .indata4  (),
  .outdata  (PCSelected )
);

four_one_mux no_name_reg_mux(
  .selector (),     //what picks the source??????????????????????????????
  .indata1  (alu_result_o   ),
  .indata2  (memDataOut     ),
  .indata3  (registerptr    ),  //where is this coming from
  .indata4  (),
  .outdata  (registerInputSelect)
);

four_one_mux dm_write_address_mux(  
  .selector (Instruction[4:3]),
  .indata1  (headptr  ),
  .indata2  (stackptr ),
  .indata3  (cacheptr ),
  .indata4  (),
  .outdata  (memWriteAddress)
);

four_one_mux dm_write_data_mux( 
  .selector (Instruction[6:5]),
  .indata1  (alu_result_o),
  .indata2  (registerptr ), 
  .indata3  (memDataOut  ),
  .indata4  (PC      ),
  .outdata  (memDataIn   )
);

four_one_mux dm_read_address_mux( 
  .selector (Instruction[4:3]),
  .indata1  (headptr ),
  .indata2  (stackptr),
  .indata3  (cacheptr),
  .indata4  (),
  .outdata  (memDataIn  )
);
endmodule
