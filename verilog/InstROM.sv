module InstROM #(parameter IW=16)(
  input       [IW-1:0] InstAddress,
  output logic[   8:0] InstOut);
   
  logic [8:0] inst_rom [2**IW];    // 2**IW elements, 9 bits each
// load machine code program into instruction ROM
  initial 
  $readmemb("instruct.txt", inst_rom);

// continuous combinational read output  
//   change the pointer (from program counter) ==> change the output
  assign InstOut = inst_rom[InstAddress];

endmodule
