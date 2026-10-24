import { Link } from "react-router-dom";
import logo from "../images/logo.png";

const Navbar = () => {
    return (
        <nav className="sticky top-0 z-50 w-full h-20 bg-white border-b border-gray-100 px-8">
            <div className="max-w-7xl mx-auto h-full flex items-center justify-between">
                {/* Logo */}
                <Link to="/" className="flex items-center cursor-pointer">
                    <img
                        src={logo}
                        alt="OCR Project"
                        className="w-44 h-auto"
                    />
                </Link>

                {/* Navigation */}
                <div className="flex items-center gap-10 font-bold">
                    <Link
                        to="/"
                        className="text-gray-700 hover:text-blue-600 transition-colors"
                    >
                        Upload
                    </Link>

                    <a
                        href="#about"
                        className="text-gray-700 hover:text-blue-600 transition-colors"
                    >
                        About
                    </a>
                </div>

                {/* Profile */}
                <div className="flex items-center gap-6">
                    <a href="#signin" className="hover:underline text-gray-700">
                        Sign In
                    </a>
                    <button className="bg-black text-white px-4 py-2 rounded-lg cursor-pointer hover:bg-gray-800 transition">
                        Get Started
                    </button>
                </div>
            </div>
        </nav>
    );
};

export default Navbar;