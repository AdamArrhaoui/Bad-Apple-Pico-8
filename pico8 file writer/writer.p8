pico-8 cartridge // http://www.pico-8.com
version 34
__lua__

bufferaddr = 0x8000

function load_file_to_mem(dest, write_cap)
    local written = 0
    if (not stat(120)) return nil
    while stat(120) do
        serial(0x800, dest + written, 1)
        written += 1
        if (written == 0x8000 or written == write_cap) print("hit write cap") break
        if (dest + written - 1 == 0xFFFF) print("hit memory cap") break
    end
    return written
end

function export_file_to_carts(out_file_name)
    if (not stat(120)) stop("File not loaded!")
    local filecount = 0
    local last_len_written = 0
    while stat(120) do
        local len_written = load_file_to_mem(bufferaddr, 0x4300)
        if (len_written == nil) return filecount, last_len_written

        filecount += 1
        cstore(0x0,bufferaddr,len_written,out_file_name .. filecount .. ".p8")
        last_len_written = len_written
        memset(bufferaddr,0x0,0x4300)
    end
    return filecount, last_len_written
end


function read_str_from_mem(addr, len)
    local out = ""
    while len != 0 do
        local readsize = len % 0x2000
        if (readsize == 0) readsize = 0x2000
        out ..= chr(peek(addr, readsize))
        addr += readsize 
        len -= readsize
    end
    return out
end


function import_str_from_carts(file_prefix, num_files, last_file_len)
    local out = ""
    for i = 1, num_files do
        local currfile = file_prefix .. i .. ".p8"
        local readlen = (i == num_files) and last_file_len or 0x4300
        reload(bufferaddr, 0x0, readlen, currfile)
        out ..= read_str_from_mem(bufferaddr, readlen)
        memset(bufferaddr,0x0,readlen)
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

while not stat(120) do
    cls()
    print([[waiting for data]])
    flip()
end

cartname = "headers"
print("Exporting file data to p8 carts... (" .. cartname .. "<1..n>.p8)")
filecount, lastfilelen = export_file_to_carts(cartname)
print("Exported data to " .. filecount .. " files.")
print("Last file had " .. lastfilelen .. " bytes written")

printh("local num_" .. cartname .. "_files = " .. filecount .. "\nlocal last_" .. cartname .. "_file_len = " .. lastfilelen, "@clip")
print("metadata copied to clipboard")

print("re-loading data from carts...")
cartdatastr = import_str_from_carts(cartname, filecount, lastfilelen)
print("re-loaded string length: " .. #cartdatastr)
-- datalen = load_file_to_mem(0x8000, 0x4300)
-- print("data loaded! Length: " .. datalen)
-- str = read_str_from_mem(0x8000, datalen)
-- print("string len: " .. #str)

-- print("storing string to datacart.p8...")
-- cstore(0x0,0x8000,0x4300,"datacart.p8")

-- print("clearing memory...")
-- memset(0x8000,0x0,0x8000)

-- print("loading Data from Cart...")
-- reload(0x8000,0x0,0x4300, "datacart.p8")

-- newstr = read_str_from_mem(0x8000, 0x4300)
-- print("Reloaded string len: " .. #newstr)

-- print("\nchecking if string is the same...")
-- for i=1,#newstr do
--     assert( sub(str, i, i)== sub(newstr, i, i), "not equal on position"..i)
-- end
-- print("ok!")

