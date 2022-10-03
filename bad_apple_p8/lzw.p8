pico-8 cartridge // http://www.pico-8.com
version 34
__lua__

function tape_bits(x,byte)
  local write,ret=0.5<<x,0
  for i=1,x do
    if byte then 
      -- overwrite (clears also bits!)
      poke2(tape_pos, byte&write!=0 and %tape_pos | tape_bit or %tape_pos & ~tape_bit)
    else
      if (%tape_pos & tape_bit !=0) ret |=write
    end
    tape_bit >>>=1
    write >>>=1
    if (tape_bit<1) tape_pos+=2 tape_bit=0x8000
  end
  return ret
end
  
function tape_set(adr)
 tape_pos,tape_bit=adr,0x8000
end

function compress(dest,src,srclen)
  local dictionary, dict_size, w,bitsize, c = {}, 255, "",8
  
  tape_set(dest+2) -- 2 bytes for token count
  
  for i = 0, 255 do
    dictionary[chr(i)] = i
  end
  for i = 1, srclen do
    c = chr(@src) src+=1
    if dictionary[w .. c] then
      w = w .. c
    else
      tape_bits(bitsize,dictionary[w])
      dict_size += 1
      if (1<<bitsize<=dict_size) bitsize+=1
      dictionary[w .. c] = dict_size
      w = c
    end
  end
    
  tape_bits(bitsize,dictionary[w])
  --dict_size +=1
  
  poke2(dest,dict_size-254) -- store token-count 
  return tape_pos-dest+2 -- tape_pos is the current write position, so add 2!
end


function compress_str(dest, src_str)
  local dictionary, dict_size, w,bitsize, c = {}, 255, "",8
  
  tape_set(dest+2) -- 2 bytes for token count
  
  for i = 0, 255 do
    dictionary[chr(i)] = i
  end
  for i = 1, #src_str do
    c = sub(src_str, i, i)
    if dictionary[w .. c] then
      w = w .. c
    else
      tape_bits(bitsize,dictionary[w])
      dict_size += 1
      if (1<<bitsize<=dict_size) bitsize+=1
      dictionary[w .. c] = dict_size
      w = c
    end
  end
    
  tape_bits(bitsize,dictionary[w])
  --dict_size +=1
  
  poke2(dest,dict_size-254) -- store token-count 
  return tape_pos-dest+2 -- tape_pos is the current write position, so add 2!
end

 
function decompress(dest,src)
  local dictionary, bitsize,odest,w,entry = {}, 9,dest
  tape_set(src+2)
  
  for i = 0, 255 do
    dictionary[i] = chr(i)
  end
  
  w=dictionary[tape_bits(8)]
  poke(dest,ord(w)) dest+=1
  
  for i = 2, %src do
    entry = dictionary[ tape_bits(bitsize)] or w .. sub(w, 1, 1)
    
    -- poke in combination with "multi"-ord is buggy - don't use it
    -- it will cause random crashes of pico-8!
    for i=1,#entry do
      poke(dest,ord(entry,i)) dest+=1
    end
 
    add(dictionary,w .. sub(entry, 1, 1))
    if (1<<bitsize<=#dictionary+1) bitsize+=1
 
    w = entry
  end
  return dest-odest
end

function decompress_to_str(src)
  local dictionary, bitsize,w,entry = {}, 9
  output = ""
  tape_set(src+2)
  
  for i = 0, 255 do
    dictionary[i] = chr(i)
  end
  
  w=dictionary[tape_bits(8)]
  output ..= w
  
  for i = 2, %src do
    entry = dictionary[ tape_bits(bitsize)] or w .. sub(w, 1, 1)
    
    -- poke in combination with "multi"-ord is buggy - don't use it
    -- it will cause random crashes of pico-8!
    for i=1,#entry do
      output ..= chr(ord(entry,i))
    end
 
    add(dictionary,w .. sub(entry, 1, 1))
    if (1<<bitsize<=#dictionary+1) bitsize+=1
 
    w = entry
  end
  return output
end


function read_mem_str(src, srclen)
	endaddr = src + srclen - 1
	out = ""
	for i = src, endaddr do
		out ..= chr(@i)
	end
	return out
end


function escape_binary_str(s)
 local out=""
 for i=1,#s do
  local c  = sub(s,i,i)
  local nc = ord(s,i+1)
  local pr = (nc and nc>=48 and nc<=57) and "00" or ""
  local v=c
  if(c=="\"") v="\\\""
  if(c=="\\") v="\\\\"
  if(ord(c)==0) v="\\"..pr.."0"
  if(ord(c)==10) v="\\n"
  if(ord(c)==13) v="\\r"
  out..= v
 end
 return out
end

#include headers.lua
source_str = headers
size=#source_str
cls()
?[[
lzw-demo
--------

demo-data: \0
]]

?"size:".. size
comsize=compress_str(0x8000,source_str)
?"compressed size:".. comsize
?"ratio:".. comsize/size*100
printh(escape_binary_str(read_mem_str(0x8000, comsize)), "@clip")
decom = decompress_to_str(0x8000)
?"decompressed size:".. #decom
?"check...\0"
for i=1,size do
  assert( sub(source_str, i, i)== sub(decom, i, i), "not equal on position"..i)
end
print("ok")

