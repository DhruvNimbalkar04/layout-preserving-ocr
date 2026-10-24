import Navbar from '../components/Navbar';
import HomeMiddle from '../components/HomeMiddle';
import UploadDoc from '../components/UploadDoc';

const Home = () => {
  return (
    <div className="min-h-screen bg-gray-50/50 pb-20">
      <Navbar />
      <HomeMiddle />
      <UploadDoc />
    </div>
  );
};

export default Home;
