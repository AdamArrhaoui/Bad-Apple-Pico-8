pico-8 cartridge // http://www.pico-8.com
version 34
__lua__


function _init()
	local num_video_files = 6
	local last_video_file_len = 16750
	local num_headers_files = 2
	local last_headers_file_len = 13910
	
	print("loading video...")
	video = import_str_from_carts("video", num_video_files, last_video_file_len)
	print("video len: " .. tostr(#video>>>16, 0x2))

	
	print("loading frame headers...")
	headers = import_str_from_carts("headers", num_headers_files, last_headers_file_len)
	print("headers len: " .. #headers)
	
	
	print("loading music...")
	reload(0X3100, 0X3100, 0X1200, "bapplesound.p8")
	
	palt(0, false)
	
	frame = 1
	vid_len = #headers \ 6
	num_tiles = 0

	fps = 24
	//how big pixels are
	pxsize = 4
	//how big tiles are in big pixels
	tsize = 4
	//y coordinate of top of screen
	topy = 16

	col_b = 0
	col_w = 7

	wtiles = 8
	htiles = 6

	wait = 30

	testmode = false
	testmodestr = ""
	cls()
	main()
end

function main()

	while true do
	 //fps limiter
		if wait > 0 then
			wait -= 1
			goto next_frame
		end
		if (btnp(🅾️)) testmode = not testmode
		
		if testmode then
			if (not btnp(❎)) goto next_frame
			testmodestr = ""
		end
		
		if (frame == 1) music()
		
		if frame < vid_len then
	--		fstr = video[frame]
	--		if (#fstr == 0) frame += 1 return
			//get frame info

			rowheads = {ord(headers, 6*frame-5, 6)}
			// loop through rows/tiles
			for ty = 0, #rowheads-1 do
				local row = rowheads[ty + 1]
				row = 255 - row
				testmodestr ..= " " .. row
				if row != 0 then
					for tx = 0, 7 do
						if (0x1 << (7-tx)) & row ~= 0 then
							local ttop, tbot = ord(video, num_tiles * 2 + 1, 2)
							ttop = 255 - ttop
							tbot = 255 - tbot
							num_tiles += 1
							filltile(tx, ty, ttop, tbot)
							// make sure string indices don't overflow
							if num_tiles == 0x3FFF then
								video = sub(video, 0x7FFF)
								num_tiles = 0
							end
						end
					end
				end
			end
		else
			cls()
			return
		end
		frame += 1
		if ((frame % 4) == 0) wait = 1
		::next_frame::
		flip()
	end
end


function import_str_from_carts(file_prefix, num_files, last_file_len)
	local bufferaddr = 0x8000
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


--function _draw()
---- cls(0)
----	sspr(0, 0, wtiles*tsize, htiles*tsize, 0, topy, 128, 128 - topy*2)
--	if testmode then
--		rectfill(0, 0, 127, topy-1, 0)
--		cursor(0, 0, 7)
--		print("frame:" .. frame .. " num tiles: " .. num_tiles)
--		
----		if (not fhead or not rowskip) return
----		print("head: " .. fhead .. " rs: ".. rowskip .. " fs: " .. fskip, 0, 100)
--
--		printh(testmodestr, '@clip')
--
--	end
--end


//fills tile in spritesheet
function filltile(tx, ty, topnum, botnum)
	//tx, ty are tile coordinates
	//tnum is tile pixel bitfield as num
	local xstart = tx * tsize * 4
	local ystart = ty * tsize * 4 + topy
	local curnum = topnum
	
	for i = 0, 15 do
		local px = xstart + (i % 4) * 4
		local py = ystart + (i \ 4) * 4
		if (i == 8) curnum = botnum
		if (curnum >>> (7 - i%8)) & 1 == 1 then
			flippixels(px, py, 4)
		end
	end
end


function flippixels(x, y, w)
	local oldcol = pget(x, y)
	local newcol = (oldcol == col_b) and col_w or col_b
	rectfill(x, y, x+w-1, y+w-1, newcol)
--	print(x .. " " .. y .. " " .. w)
end


