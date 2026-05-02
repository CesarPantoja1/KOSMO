import React from 'react';

const RootNavbar = () => {
	return (
		<nav className='w-full h-16 px-4 bg-gray-800 text-white flex items-center justify-between'>
			<div>
				<span>KOSMO</span>
			</div>

			<div>
				<span>Claude</span>
				<span> </span>
				<span>Profile</span>
			</div>
		</nav>
	);
};

export default RootNavbar;
